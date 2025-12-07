# Batch Job Generator

A general-purpose batch job generator designed for HPC environments. 

User provides:
- a master job template (.js, .mjs)
- any input list/matrix filepath required for job specifications
- a config file with all the above information documented

The scripts runs on the system input of config filename. 

The config should be formatted as `key=values` pairs per row. 

A `key` maybe named arbitrarily at user's discretion, but it must match with the placeholder name used in the master job template. 

A `value` accepts three types of input: a filepath, a filepath with a column index specified, a Python-style patterns with `{key}`. 

In general, the config defines the input/output filepaths, job directories, and job settings, but they can be structured in any manner and in any numbers of keys at user's convenience. 

The script will resolve all the placeholders, expands the rows of the config input, generate the jobs according to the input data length, and specify the job setting and job dependence in a separate submission file, ready to be submitted the HPC system. 

In short:

`Config in->Master template, Lists/Matrices->Batch jobs out`

No workflow assumptions. No fixed naming rules. Flexible for generic job generation in any HPC system. 

## Key features

- `key=values` per line. Invalid lines or empty lines will be skipped. Comment lines (`#...`) will be skipped.
- Quotes and whitespace around keys/values are automatically stripped.
- Automatic classification of values:
  - strings containing `{...}` -> patterns
  - filepath::idx -> matrix column input
  - filepath/constant string
- All filepaths will be checked for existence. If not existent, the value is downgraded to a constant string value and a warning message is issued.
  - in the case of matrix input, both the filepath and the column index will be checked for existence. Proper error messages would be issued if needed.
- For the pattern-type values, pure number keys are accepted, and normal python formatting syntax is accepted.
  - The common syntax associated with HPC submission commands are encoded to recognized this type of input. For this type of patterns, multiple keys can be entered into the `{...}` with any delimiter.
  -       
