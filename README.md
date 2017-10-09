# fsperf

fsperf is a performance testing framework built around
[fio](https://github.com/axboe/fio).  The goal is to provide a simple to run
framework for file system developers to be able to check their patches and make
sure they do not regress in performance.  Adding new tests is as easy as adding
a .fio file to the tests directory.

# Configuration

In order to configure the suite you need to create a `local.cfg` file in the
base of the fsperf directory.  This file takes the format normal INI files.  The
options that can be specified are

  * `mkfs` - if specified this will be run between every test.  This is the full
    mkfs command needed for your test environment.
  * `mount` - the command to mount the fs.  If specified the fs will be
    unmounted between each test.
  * `directory` - the directory to run the fio jobs in.  This _must_ be
    specified regardless of wether you mount or mkfs in between runs.

The section that gets run if you don't specify an option is `default`.  So a
sample local.cfg would look like this

```
[default]
mkfs=mkfs.btrfs -f /dev/nvme0n1
mount=mount -o noatime /dev/nvme0n1 /mnt/btrfs-test
directory=/mnt/btrfs-test
```

You can specify multiple configurations per file, and switch between them with
the `-c` option for fsperf.

# Setup

The only thing that needs to be done before hand is to create your `local.cfg`
and run the command

```
./setup
```

In the main directory of fsperf.  This will initialize the sqlite database that
will contain the results of the fio runs.

# How to run

Once you've setup your `local.cfg` you simply run

```
./fsperf
```

and wait for the suite to finish.  The complete data set that fio produces will
be stored in the database, but fsperf only compares `iops`, `io_kbytes`, and
`bw` for reads, writes and trim operations.  The intent is to cover the basics
and have as few false positives as possible.  Future work will include the
ability to visualize more data to be able to spot trends.  If desired you can
run

```
./fsperf --latency
```

To include comparisons of min and max latency.  However these can be pretty
jittery between runs and may be less useful.

# Understanding the comparisons

We only compare the last run of the given test with the given configuration.  So
if you have multiple sections in your configuration file, such as the following

```
[default]
directory=/mnt/btrfs-test

[xfs]
directory=/mnt/xfs-tests
```

Only tests in the same configuration will be compared against each other.
Future work will include the ability to compare with other configurations, but
currently you can just change your local.cfg if you wish to compare runs of
different configurations.

# Disabling tests

Sometimes you may need to disable a test, so simply add the test name to it's
own line in the `disabled-tests` file in the root of the project directory.
