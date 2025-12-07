# -*- coding: utf-8 -*-
"""
Created on Sun Dec  7 00:55:14 2025

@author: Ding Zhang
"""
from collections import defaultdict
import re
import pandas as pd
from pathlib import Path
import os
import sys

def parse_config(path):
    config = {}
    with open(path,'r') as f:
        filestr = f.read()
    lines = filestr.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line[0]=='#' or len(line.split('='))!=2:
            continue
        key,val = line.split('=')
        key,val = key.strip().strip('"').strip("'"),val.strip().strip('"').strip("'")
        config[key] = val
    return config
 
def classify_spec(config):
    #check_jobname(config)    
    spec = defaultdict(list)
    for key,val in config.items():
        if '::' in val:
            typ = 'matrix' 
        elif '{' in val and '}' in val:
            typ = 'pattern'
            if 'uds' in val and '-r' in val and '-z' in val:
                typ = 'vsub'
                pattern = re.compile(r'\{([^{}]+)\}')
                config[key] = pattern.sub(repl,config['vsub'])
        elif '.js' in val or '.mjs' in val:
            typ = 'mst'
            if not os.path.exists(val):
                raise Exception(f"Path '{val}' does not exist")
        elif os.path.exists(val): 
            typ = 'list'
        else: 
            typ = 'constant'
        spec[typ].append(key)
    if 'constant' in spec:
        if 'jobname' in spec['constant']:
            print("Warning: jobname is registered as a constant, not list")
        else:
            print(f'Attention: there are constants in the config: {spec["constant"]}')
    if 'mst' not in spec:
        mst_path = input("Mst Job Path: ").strip().strip('"').strip("'")
        if not os.path.exists(mst_path):
            raise Exception(f"Path '{mst_path}' does not exist")
        spec['mst'].append('mst')
        config['mst'] = mst_path
    #reorder_patterned(config,spec)
    return spec
 
def check_jobname(config):
    for key,val in config.items():
        if '{' in val and '}' in val and 'uds' in val and '-r' in val and '-z' in val:
            m = re.search(r'\{([^{}]+)\}\s*uds',val)
            if m:
                jobkey = m.group(1).strip()
                if jobkey !='jobname':
                    config['jobname'] = config.pop(jobkey)
                    for key,val in config.items(): config[key] = val.replace('{'+jobkey+'}','{jobname}')
                return 
    pattern = re.compile(r'job(s)?[_-]*(name|key)?(s)?(\d{1})?',re.IGNORECASE)
    found = [k for k in config if pattern.fullmatch(k)]
    if len(found)==1:
        jobkey = found[0]
        if jobkey !='jobname':
            config['jobname'] = config.pop(jobkey)
            for key,val in config.items(): config[key] = val.replace('{'+jobkey+'}','{jobname}')
        return
    if len(found)>1:
        jobkey = input('Which key is the jobname?').strip().strip('"').strip("'")
        if jobkey in config:
            config['jobname'] = config.pop(jobkey)
            for key,val in config.items(): config[key] = val.replace('{'+jobkey+'}','{jobname}')
            return
        if re.fullmatch(r'(no|none|na|n\\a|n/a|not applicable)?[,.!;]?',jobkey,re.I):
            bool_job = 0
        else:
            raise Exception("Key entry not in config")
    if not found:
        bool_like=input('Have you entered the jobkey (y/n)?').strip().strip('"').strip("'")
        if re.fullmatch(r'(y|yes|aye|en|yes,I did|right|of course)[,.!;]?',bool_like,re.I):
            bool_job = 1
        else:
            bool_job = 0
    if not bool_job: 
        jobname_val = input('Please enter the path/pattern for jobname:').strip().strip('"').strip("'")
        config['jobname'] = jobname_val
        return 
    jobkey = input('Which key is the jobname?').strip().strip('"').strip("'")
    if jobkey in config:
        config['jobname'] = config.pop(jobkey)
        for key,val in config.items(): config[key] = val.replace('{'+jobkey+'}','{jobname}')
        return
    raise Exception("Key entry not in config")
 
def repl(match):
    inside = match.group(1).strip()
    parts = re.split(r'[,\s\t:;.~`]+',inside)
    parts_reg = ['{'+p.strip()+'}' for p in parts if p]
    return ",".join(parts_reg)
def reorder_patterned(config,spec):
    if 'pattern' not in spec:
        return
    visit,ring = set(),set()
    key_set = set(config.keys())
    pat_set = set(spec['pattern'])
    pattern = re.compile(r'\{([^:}]+)(?::[^:}]*)?\}')
    res = []
    def dfs(key):
        if key in ring:
            raise Exception(f"Ring detected. check '{key}'")
        if key not in key_set:
            raise Exception(f"Key: '{key}', not in config")
        if key in visit:
            return
        val = config[key]
        ring.add(key)
        for kk in pattern.findall(val):
            kk = kk.strip()
            dfs(kk)
        if key in pat_set:
            res.append(key)
        ring.discard(key)
        visit.add(key)
    for key in spec['pattern']:
        if key not in visit:
            dfs(key)
    spec['pattern'] = res
def number_key_preprocess(config,spec):
    if 'pattern' not in spec:
        return
    pattern = re.compile(r'\{([^:}]+)(?::[^:}]*)?\}')
    for key in spec['pattern']:
        val = config[key]
        for kk in pattern.findall(val):
            if kk.isdigit():
                config[key] = val.replace(kk,'_'+kk)
def read_spec(config,spec):
    list_specs = {}
    len_specs = 0
    for key in spec['list']:
        df = pd.read_csv(config[key],sep=r'\s+',header=None)
        list_specs[key] = list(df[0])
        len_specs = len(list(df[0]))
    for key in spec['matrix']:
        if len(config[key].split('::')) !=2:
            raise Exception(f"'{key}': more than 1 column specified.")
        filepath,col_idx = config[key].split('::')
        filepath,col_idx = filepath.strip().strip('"').strip("'"),int(col_idx.strip())
        if not os.path.exists(filepath):
            raise Exception(f"Path '{filepath}' does not exist")
        df = pd.read_csv(filepath,sep=r'\s+',header=None)
        if df.shape[1]<col_idx:
            raise Exception(f"Column index '{col_idx}' exceeds maximum column number of '{filepath}'")
        list_specs[key] = list(df[col_idx-1])
        len_specs = len(list(df[col_idx-1]))
    for key in list_specs:
        if len(list_specs[key]) !=len_specs:
            raise Exception(f"Data length not uniform across different inputs, check '{key}'")
    for key in spec['constant']:
        list_specs[key] = [config[key]]*len_specs
    job_specs = []
    for row in range(len_specs):
        job_specs_row = {}; help_row = {}
        if 'vsub' in spec: 
            help_row_vsub = {}
        job_specs_row['row'] = row+1
        for key in list_specs:
            job_specs_row[key] = list_specs[key][row]     
            if key.isdigit():
                key2 = '_'+key
                help_row[key2] = list_specs[key][row]
                if 'vsub' in spec: help_row_vsub[key2] = Path(str(list_specs[key][row])).name
            else:
                help_row[key] = list_specs[key][row]
                if 'vsub' in spec: help_row_vsub[key] = Path(str(list_specs[key][row])).name
        for key in spec['pattern']:
            pat_line = config[key]
            rep_line = pat_line.format(**help_row)
            job_specs_row[key] = rep_line 
            if key.isdigit():
                key2 = '_'+key
                help_row[key2] = rep_line
                if 'vsub' in spec: help_row_vsub[key2] = Path(str(rep_line)).name
            else:
                help_row[key] = rep_line
                if 'vsub' in spec: help_row_vsub[key] = Path(str(rep_line)).name
        for key in spec['vsub']:
            pat_line = config[key]
            rep_line = pat_line.format(**help_row_vsub)
            job_specs_row[key] = rep_line
        job_specs.append(job_specs_row)
    return job_specs
 
def job_gen(config,spec,job_specs):
    mst_path = config[spec['mst'][0]].strip("'").strip('"')
    with open(mst_path,'r') as f:
        mst = f.read()
    vsub = ''
    for entry in job_specs:
        jobpath = Path(entry['jobname']).parent
        jobpath.mkdir(parents=True,exist_ok=True)
        cnt = mst
        for key, val in entry.items():
            cnt = cnt.replace(key,str(val))
        jobname = entry['jobname'] if entry['jobname'].endswith('.js') else entry['jobname']+'.js'
        with open(jobname,'w') as f:
            f.write(cnt)
        if 'vsub' in spec:
            for key in spec['vsub']:
                vsub+= entry[key]+'\n'
    if 'vsub' in spec:
        with open(jobpath/'vsub','w') as f:
            f.write(vsub)
            
os.chdir(os.path.dirname(os.path.abspath(__file__)))
config_path = sys.argv[1:]
if len(config_path)==0:
    pattern = re.compile(r'(conf(?:ig)?|cfg)',re.I)
    cands = []
    for entry in os.scandir():
        if entry.is_file() and pattern.search(entry.name):
                cands.append(entry.name)
    if len(cands)==1:
        cpath = cands[0]
    elif len(cands)>1:
        cpath = input(f"Enter config path [{cands[0]}]:").strip().strip('"').strip("'")
        if cpath=='': cpath = cands[0]
    else:
        cpath = input("Enter config path:").strip().strip('"').strip("'")
    if not os.path.exists(cpath):
        raise Exception(f"Path '{cpath}' does not exist")
else:
    cpath = sys.argv[1]
    if not os.path.exists(cpath):
        raise Exception(f"Path '{cpath}' does not exist")
## read in config
config = parse_config(cpath)
## locate the jobname folder
check_jobname(config)
## classify the input keys/placeholders
spec = classify_spec(config)
## reorder the patterned texts according to in-degrees
reorder_patterned(config, spec)
## number keys cannot be formatted by python. need processing.
number_key_preprocess(config,spec)
## generate all the rows
job_specs = read_spec(config,spec)
## write-in
job_gen(config,spec,job_specs)





