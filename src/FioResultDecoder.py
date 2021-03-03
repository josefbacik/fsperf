import json

class FioResultDecoder(json.JSONDecoder):
    """Decoder for decoding fio result json to an object for our database

    This decodes the json output from fio into an object that can be directly
    inserted into our database.  This just strips out the fields we don't care
    about and collapses the read/write/trim classes into a flat value structure
    inside of the jobs object.

    For example
        "write" : {
            "io_bytes" : 313360384,
            "bw" : 1016,
        }

    Get's collapsed to

        "write_io_bytes" : 313360384,
        "write_bw": 1016,

    Currently any dict under 'jobs' get's dropped, with the exception of 'read',
    'write', and 'trim'.  For those sub sections we drop any dict's under those.

    Attempt to keep this as generic as possible, we don't want to break every
    time fio changes it's json output format.
    """
    _ignore_types = ['dict', 'list']
    _override_keys = ['lat_ns', 'clat_ns']
    _io_ops = ['read', 'write', 'trim']

    def _extract_percentiles(self, new_job, iotype, key, percentiles):
        for p,pval in percentiles.items():
            p = float(p)
            if p.is_integer():
                p = int(p)
            collapsed_key = "{}_{}_p{}".format(iotype, key, p)
            new_job[collapsed_key] = pval

    def decode(self, json_string):
        """This does the dirty work of converting everything"""
        default_obj = super(FioResultDecoder, self).decode(json_string)
        obj = {}
        obj['jobs'] = []
        for job in default_obj['jobs']:
            new_job = {}
            for key,value in job.items():
                if key not in self._io_ops:
                    if value.__class__.__name__ in self._ignore_types:
                        continue
                    new_job[key] = value
                    continue
                for k,v in value.items():
                    if k in self._override_keys:
                        for subk,subv in v.items():
                            if subk == "percentile":
                                self._extract_percentiles(new_job, key, k, subv)
                                continue
                            collapsed_key = "{}_{}_{}".format(key, k, subk)
                            new_job[collapsed_key] = subv
                        continue
                    if v.__class__.__name__ in self._ignore_types:
                        continue
                    collapsed_key = "{}_{}".format(key, k)
                    new_job[collapsed_key] = v
            obj['jobs'].append(new_job)
        return obj
