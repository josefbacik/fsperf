extern crate image;

use clap::Parser;
use core::ops::{Deref, DerefMut};
use image::{ImageBuffer, Pixel, Rgb, RgbImage};
use fast_hilbert::h2xy;
use std::collections::{BTreeMap, HashSet};
use std::collections::Bound::{Included, Unbounded};
use std::error;
use std::fmt;
use std::fs;
use statrs::statistics::Data;
use statrs::statistics::Max;
use statrs::statistics::Min;
use statrs::statistics::Distribution;
use statrs::statistics::OrderStatistics;
use serde_json::json;

const K: u64 = 1 << 10;
const BLOCK: u64 = 4 * K;
const WHITE_PIXEL: Rgb<u8> = Rgb([255, 255, 255]);
const RED_PIXEL: Rgb<u8> = Rgb([255, 0, 0]);
const GREEN_PIXEL: Rgb<u8> = Rgb([0, 255, 0]);
const BLUE_PIXEL: Rgb<u8> = Rgb([0, 0, 255]);

#[derive(Debug, Hash, Eq, PartialEq)]
enum ExtentType {
    Data,
    Metadata
}
#[derive(Debug, PartialEq)]
enum AllocType {
    BlockGroup,
    Extent(ExtentType)
}

#[derive(Debug)]
enum FragViewError {
    BeforeStart(u64, u64),
    PastEnd(u64, u64),
    MissingBg(u64),
    MissingExtent(u64, u64),
    Parse(String),
    TooMuchFree(u64, u64),
}

impl error::Error for FragViewError { }

impl fmt::Display for FragViewError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            FragViewError::BeforeStart(e, bg) => write!(f, "extent start {} before bg start {}", e, bg),
            FragViewError::PastEnd(e, bg) => write!(f, "extent end {} past bg end {}", e, bg),
            FragViewError::MissingBg(bg) => write!(f, "missing bg {}", bg),
            FragViewError::MissingExtent(e, bg) => write!(f, "missing extent {} in bg {}", e, bg),
            FragViewError::Parse(s) => write!(f, "invalid allocation change {}", s),
            FragViewError::TooMuchFree(free, len) => write!(f, "bg has more free space {} than size {}", free, len),
        }
    }
}

type BoxResult<T> = Result<T, Box<dyn error::Error>>;

impl AllocType {
    fn from_str(type_str: &str) -> BoxResult<Self> {
        if type_str == "BLOCK-GROUP" {
            Ok(AllocType::BlockGroup)
        } else if type_str == "METADATA-EXTENT" {
            Ok(AllocType::Extent(ExtentType::Metadata))
        } else if type_str == "DATA-EXTENT" {
            Ok(AllocType::Extent(ExtentType::Data))
        } else {
            Err(FragViewError::Parse(String::from(type_str)))?
        }
    }
}

#[derive(Debug, PartialEq)]
struct AllocId {
    alloc_type: AllocType,
    offset: u64,
}

#[derive(Debug, PartialEq)]
enum AllocChange {
    Insert(AllocId, u64),
    Delete(AllocId),
}

impl AllocChange {
    fn from_dump(dump_line: &str) -> BoxResult<Self> {
        let vec: Vec<&str> = dump_line.split(" ").collect();
        let change_str = vec[0];
        let type_str = vec[1];
        let alloc_type = AllocType::from_str(type_str)?;
        let offset: u64 = vec[2].parse().unwrap();
        let eid = AllocId { alloc_type, offset };
        if change_str == "INS" {
            let len: u64 = vec[3].parse().unwrap();
            Ok(AllocChange::Insert(eid, len))
        } else if change_str == "DEL" {
            Ok(AllocChange::Delete(eid))
        } else {
            Err(FragViewError::Parse(String::from(change_str)))?
        }
    }
}

#[derive(Debug)]
struct BlockGroupFragmentation {
    len: u64, // block group len
    total_free: u64, // sum of all free extents
    max_free: u64, // largest free extent
}

impl BlockGroupFragmentation {
    fn new(len: u64) -> Self {
        Self { len: len, total_free: 0, max_free: 0 }
    }
    fn add_free(&mut self, len: u64) -> BoxResult<()>{
        self.total_free = self.total_free + len;
        if self.total_free > self.len {
            Err(FragViewError::TooMuchFree(self.total_free, self.len))?
        }
        if len > self.max_free {
            self.max_free = len;
        }
        Ok(())
    }
    fn percentage(&self) -> f64 {
        if self.total_free == 0 {
            return 0.0;
        }
        100.0 * (1.0 - ((self.max_free as f64) / (self.total_free as f64)))
    }
}

#[derive(Debug)]
struct BlockGroup {
    offset: u64,
    len: u64,
    extents: BTreeMap<u64, u64>,
    extent_types: HashSet<ExtentType>,
    img: RgbImage,
    next_extent_color: Rgb<u8>,
    dump: bool,
    dump_count: usize,
}

// fast_hilbert outputs 4 regions of size 256x256
// TODO: why???
fn bg_dim(_bg_len: u64) -> u32 {
    512
}

fn bg_block_to_coord(_dim: u32, block_offset: u64) -> (u32, u32) {
    h2xy::<u32>(block_offset)
}

fn global_to_bg(bg_start: u64, offset: u64) -> u64 {
    offset - bg_start
}

fn byte_to_block(offset: u64) -> u64 {
    offset / BLOCK
}

// RUST BS:
// illegal double borrow for:
// for ext in self.extents { // immutable borrow
//   self.draw_extent(ext) // mutable borrow, doesn't touch extents
// }
// to fix it without adding a copy, need to pull out this free function
fn draw_extent<P, C>(
    img: &mut ImageBuffer<P, C>,
    bg_start: u64,
    extent_offset: u64,
    extent_len: u64,
    dim: u32,
    pixel: P,
) where
    P: Pixel + 'static,
    C: Deref<Target = [P::Subpixel]> + DerefMut,
{
    let ext_bg_off = global_to_bg(bg_start, extent_offset);
    let ext_block_bg_off = byte_to_block(ext_bg_off);
    let nr_blocks = byte_to_block(extent_len);
    let ext_block_bg_end = ext_block_bg_off + nr_blocks;
    for bg_block in ext_block_bg_off..ext_block_bg_end {
        let (x, y) = bg_block_to_coord(dim, bg_block);
        img.put_pixel(x, y, pixel);
    }
}

impl BlockGroup {
    fn new(offset: u64, len: u64, dump: bool) -> Self {
        let dim = bg_dim(len);
        BlockGroup {
            offset: offset,
            len: len,
            extent_types: HashSet::new(),
            extents: BTreeMap::new(),
            img: ImageBuffer::from_pixel(dim, dim, WHITE_PIXEL),
            next_extent_color: RED_PIXEL,
            dump: dump,
            dump_count: 0,
        }
    }

    fn get_next_extent_color(&mut self) -> Rgb<u8> {
        match self.next_extent_color {
            RED_PIXEL => self.next_extent_color = GREEN_PIXEL,
            GREEN_PIXEL => self.next_extent_color = BLUE_PIXEL,
            BLUE_PIXEL => self.next_extent_color = RED_PIXEL,
            _ => panic!("invalid extent color!"),
        }
        self.next_extent_color
    }

    fn ins_extent(&mut self, offset: u64, len: u64) -> BoxResult<()> {
        if offset < self.offset {
            return Err(FragViewError::BeforeStart(offset, self.offset))?;
        }
        if offset + len > self.offset + self.len {
            return Err(FragViewError::PastEnd(offset+len, self.offset+self.len))?;
        }
        self.extents.insert(offset, len);
        let color = self.get_next_extent_color();
        self.draw_extent(offset, len, color);
        if self.dump {
            self.dump_next()?;
        }
        Ok(())
    }

    fn del_extent(&mut self, offset: u64) -> BoxResult<()> {
        let extent = self.extents.remove(&offset);
        match extent {
            Some(len) => {
                self.draw_extent(offset, len, WHITE_PIXEL);
                if self.dump {
                    self.dump_next()?;
                }
                Ok(())
            },
            None => {
                Err(FragViewError::MissingExtent(offset, self.offset))?
            }
        }
    }

    fn fragmentation(&self) -> BoxResult<BlockGroupFragmentation> {
        let mut bg_frag = BlockGroupFragmentation::new(self.len);
        let mut last_extent_end = self.offset;
        for (off, len) in &self.extents {
            if *off > last_extent_end {
                let free_len = off - last_extent_end;
                bg_frag.add_free(free_len)?;
            }
            last_extent_end = off + len;
        }
        let bg_end = self.offset + self.len;
        if last_extent_end < bg_end {
            let free_len = bg_end - last_extent_end;
            bg_frag.add_free(free_len)?;
        }
        Ok(bg_frag)
    }

    fn draw_extent(&mut self, extent_offset: u64, len: u64, pixel: Rgb<u8>) {
        let dim = bg_dim(self.len);
        draw_extent(&mut self.img, self.offset, extent_offset, len, dim, pixel)
    }

    fn name(&self) -> String {
        let types: Vec<String> = self.extent_types.iter().map(|et| format!("{:?}", et)).collect();
        let type_names = if types.is_empty() { String::from("Empty") } else { types.join("-") };
        format!("{}-{}", type_names, self.offset)
    }

    fn dump_img(&self, f: &str) -> BoxResult<()> {
        let d = self.name();
        if d.contains("Meta") {
            return Ok(());
        }
        if d.contains("Empty") {
            return Ok(());
        }
        let _ = fs::create_dir_all(&d)?;
        let path = format!("{}/{}.png", d, f);
        Ok(self.img.save(path)?)
    }

    fn dump_frag(&self) -> BoxResult<()> {
        if !self.name().contains("Data") {
            return Ok(());
        }
        let frag = self.fragmentation()?;
        println!("{}: {} {:?}", self.offset, frag.percentage(), frag);
        Ok(())
    }

    fn dump_next(&mut self) -> BoxResult<()> {
        let f = format!("{}", self.dump_count);
        self.dump_img(&f)?;
        self.dump_count = self.dump_count + 1;
        Ok(())
    }
}

#[derive(Debug)]
struct SpaceInfo {
    block_groups: BTreeMap<u64, BlockGroup>,
    dump: bool,
}

impl SpaceInfo {
    fn new() -> Self {
        SpaceInfo {
            block_groups: BTreeMap::new(),
            dump: false,
        }
    }
    fn ins_block_group(&mut self, offset: u64, len: u64) {
        self.block_groups
            .insert(offset, BlockGroup::new(offset, len, self.dump));
    }
    fn del_block_group(&mut self, offset: u64) {
        self.block_groups.remove(&offset);
    }
    fn find_block_group(&mut self, offset: u64) -> BoxResult<&mut BlockGroup> {
        let r = self.block_groups.range_mut((Unbounded, Included(offset)));
        match r.last() {
            Some((_, bg)) => Ok(bg),
            None => Err(FragViewError::MissingBg(offset))?,
        }
    }
    fn ins_extent(&mut self, extent_type: ExtentType, offset: u64, len: u64) -> BoxResult<()> {
        let offset = offset;
        let bg = self.find_block_group(offset)?;
        bg.ins_extent(offset, len)?;
        bg.extent_types.insert(extent_type);
        Ok(())
    }
    fn del_extent(&mut self, offset: u64) -> BoxResult<()> {
        let bg = self.find_block_group(offset)?;
        bg.del_extent(offset)?;
        Ok(())
    }

    fn handle_alloc_change(&mut self, alloc_change: AllocChange) -> BoxResult<()> {
        match alloc_change {
            AllocChange::Insert(AllocId { alloc_type, offset }, len) => match alloc_type {
                AllocType::BlockGroup => {
                    self.ins_block_group(offset, len);
                }
                AllocType::Extent(extent_type) => {
                    self.ins_extent(extent_type, offset, len)?;
                }
            },
            AllocChange::Delete(AllocId { alloc_type, offset }) => match alloc_type {
                AllocType::BlockGroup => {
                    self.del_block_group(offset);
                }
                _ => {
                    self.del_extent(offset)?;
                }
            },
        }
        Ok(())
    }

    fn dump_imgs(&self, name: &str) -> BoxResult<()> {
        for (_, bg) in &self.block_groups {
            bg.dump_img(name)?;
        }
        Ok(())
    }

    fn dump_raw(&self) -> BoxResult<()> {
        for (_, bg) in &self.block_groups {
            bg.dump_frag()?;
        }
        Ok(())
    }

    fn dump_stats(&self) -> BoxResult<()> {
        let mut pctv: Vec<f64> = Vec::new();
        let mut total_bgs = 0;
        for (_, bg) in &self.block_groups {
            total_bgs = total_bgs + 1;
            if !bg.name().contains("Data") {
                continue;
            }
            let frag = bg.fragmentation()?;
            if frag.percentage() == 0.0 {
                continue;
            }
            pctv.push(frag.percentage());
        }
        let mut d = Data::new(pctv);
        let mean = match d.mean() {
            Some(m) => m,
            None => 0.0
        };
        let mut min = 0.0;
        let mut p50 = 0.0;
        let mut p95 = 0.0;
        let mut p99 = 0.0;
        let mut max = 0.0;
        if d.len() > 0 {
            min = d.min();
            p50 = d.median();
            p95 = d.percentile(95);
            p99 = d.percentile(99);
            max = d.max();
        }
        let json = json!({
            "bg_count": total_bgs,
            "fragmented_bg_count": d.len(),
            "frag_pct_mean": mean,
            "frag_pct_min": min,
            "frag_pct_p50": p50,
            "frag_pct_p95": p95,
            "frag_pct_p99": p99,
            "frag_pct_max": max
        });
        println!("{}", json);
        Ok(())
    }

    fn handle_file(&mut self, f: &str) -> BoxResult<()> {
        let contents = fs::read_to_string(&f)?;
        for line in contents.split("\n") {
            if line.is_empty() {
                continue;
            }
            let ac = AllocChange::from_dump(line)?;
            self.handle_alloc_change(ac)?;
        }
        Ok(())
    }
}

/// Analyze and visualize btrfs block group fragmentation
#[derive(Parser, Debug)]
#[clap(author, version, about, long_about = None)]
struct Args {
    /// btrd frag dump file name
    #[clap(value_parser)]
    file: String,

    /// Whether or not to dump fragmentation stats
    #[clap(short, long, value_parser, default_value_t = true)]
    stats: bool,

    /// Whether or not to dump fragmentation images
    #[clap(short, long, value_parser, default_value_t = false)]
    images: bool,

    /// Whether or not to dump raw bg fragmentation data
    #[clap(short, long, value_parser, default_value_t = false)]
    raw: bool,
}

fn main() -> BoxResult<()> {
    let args = Args::parse();
    let mut si = SpaceInfo::new();
    si.handle_file(&args.file)?;
    if args.stats {
        si.dump_stats()?;
    }
    if args.images {
        si.dump_imgs(&args.file)?;
    }
    if args.raw {
        si.dump_raw()?;
    }
    Ok(())
}

#[cfg(test)]
mod test {
    const M: u64 = 1 << 20;
    const G: u64 = 1 << 30;


    use super::*;
    #[test]
    fn parse_dump_lines() {
        let dummy_dump_line = "INS BLOCK-GROUP 420 42";
        let ac = AllocChange::from_dump(dummy_dump_line).unwrap();
        assert_eq!(
            ac,
            AllocChange::Insert(
                AllocId {
                    alloc_type: AllocType::BlockGroup,
                    offset: 420
                },
                42
            )
        );

        let dummy_dump_line = "DEL BLOCK-GROUP 420";
        let ac = AllocChange::from_dump(dummy_dump_line).unwrap();
        assert_eq!(
            ac,
            AllocChange::Delete(AllocId {
                alloc_type: AllocType::BlockGroup,
                offset: 420
            })
        );

        let dummy_dump_line = "INS DATA-EXTENT 420 42";
        let ac = AllocChange::from_dump(dummy_dump_line).unwrap();
        assert_eq!(
            ac,
            AllocChange::Insert(
                AllocId {
                    alloc_type: AllocType::Data,
                    offset: 420
                },
                42
            )
        );

        let dummy_dump_line = "DEL DATA-EXTENT 420";
        let ac = AllocChange::from_dump(dummy_dump_line).unwrap();
        assert_eq!(
            ac,
            AllocChange::Delete(AllocId {
                alloc_type: AllocType::Data,
                offset: 420
            })
        );

        let dummy_dump_line = "INS METADATA-EXTENT 420 42";
        let ac = AllocChange::from_dump(dummy_dump_line).unwrap();
        assert_eq!(
            ac,
            AllocChange::Insert(
                AllocId {
                    alloc_type: AllocType::Extent(ExtentType::Metadata),
                    offset: 420
                },
                42
            )
        );

        let dummy_dump_line = "DEL METADATA-EXTENT 420";
        let ac = AllocChange::from_dump(dummy_dump_line).unwrap();
        assert_eq!(
            ac,
            AllocChange::Delete(AllocId {
                alloc_type: AllocType::Extent(ExtentType::Metadata),
                offset: 420
            })
        );
    }
    #[test]
    fn ins_extents() {
        let mut si = SpaceInfo::new();
        si.ins_block_group(G, G);
        si.ins_block_group(2 * G, G);
        si.ins_extent(G + K, 4 * K);
        si.ins_extent(2 * G + 10 * K, 256 * M);
        assert_eq!(si.block_groups.len(), 2);
        for bg in si.block_groups.values() {
            assert_eq!(bg.extents.len(), 1);
        }
    }
    #[test]
    fn del_extents() {
        let mut si = SpaceInfo::new();
        si.ins_block_group(G, G);
        si.ins_block_group(2 * G, G);
        si.ins_extent(G + K, 4 * K);
        si.ins_extent(G + 10 * K, 256 * M);
        si.ins_extent(2 * G + 10 * K, 256 * M);
        assert_eq!(si.block_groups.len(), 2);
        si.del_extent(G + 10 * K).unwrap();
        for bg in si.block_groups.values() {
            assert_eq!(bg.extents.len(), 1);
        }
    }
    // various scenarios with missing block group
    #[test]
    fn test_no_bg() {}

    // various scenarios with invalid overlapping block_groups
    #[test]
    fn test_bg_overlap() {}

    // various scenarios with invalid overlapping extents
    #[test]
    fn test_extent_overlap() {}
}
