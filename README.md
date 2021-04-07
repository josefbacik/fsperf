# fsperf

fsperf is a performance testing framework built around
[fio](https://github.com/axboe/fio).  The goal is to provide a simple to run
framework for file system developers to be able to check their patches and make
sure they do not regress in performance.  In addition to `fio` tests, `fsperf`
supports basic timing tests and `dbench` tests.

# Configuration

In order to configure the suite you need to create a `local.cfg` file in the
base of the fsperf directory.  This file takes the format normal INI files.  You
must specify a `[main]` section with the following required options

  * `directory` - the directory to run the performance jobs in.

Then subsequently you must specify configs, which whatever name you wish to use.
These take the following optional options

  * `mkfs` - if specified this will be run between every test.  This is the full
    mkfs command needed for your test environment.
  * `mount` - the command to mount the fs.  If specified the fs will be
    unmounted between each test.
  * `device` - the device that will be used for this section.
  * `iosched` - Must match one of the options in
    `/sys/block/{device}/queue/scheduler`.

```
[main]
directory=/mnt/test

[btrfs]
device=/dev/nvme0n1
mkfs=mkfs.btrfs -f
mount=mount -o noatime
```

You can specify multiple configurations per file, and switch between them with
the `-c` option for fsperf.

# How to run

Once you've setup your `local.cfg` you simply run

```
./fsperf
```

and wait for the suite to finish.  This will run the tests found under the
tests/ directory and store the results.  The blank invocation is meant for
continuous performance testing.

## A/B testing

If you wish to do A/B testing you can do the following

```
./fsperf -p "myabtest"
<make changes>
./fsperf -p "myabtest" -t
./fsperf-clean-results myabtest
```

This will store the base results under a specific heading, "myabtest", so it
doesn't muddy any other unrelated performance results.  Then using the `-t`
option it will run the tests, and spit out a comparison table between the
baseline and the current run, and then discard the current run's results in
order to not pollute the baseline results.

The comparison compares all of the saved results, so things like `fio`'s max
latencies may be a little noisy.  In order to reduce the noise of these sort of
metrics you can do something like the following

```
./fsperf -p "myabtest" -n 5
<make changes>
./fsperf -p "myabtest" -n 5 -t
./fsperf-clean-results myabtest
```

This will run each test 5 times, which means the baseline and new results will
be averaged, and then the averages will be compared against eachother.

Finally the `fsperf-clean-results` script will delete anything that matches your
special results, so you can re-use the label in the future.

# Understanding the comparisons

We only compare the last run of the given test with the given configuration.  So
if you have multiple sections in your configuration file, such as the following

```
[btrfs]
device=/dev/nvme0n1
mkfs=mkfs.btrfs -f
mount=mount -o noatime

[xfs]
device=/dev/nvme0n1
iosched=none
mkfs=mkfs.xfs -f
mount=mount -o noatime
```

Only tests in the same configuration will be compared against each other.
Future work will include the ability to compare with other configurations, but
currently you can just change your local.cfg if you wish to compare runs of
different configurations.

# Disabling tests

Sometimes you may need to disable a test, so simply add the test name to it's
own line in the `disabled-tests` file in the root of the project directory.
