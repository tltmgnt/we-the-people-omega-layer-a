"""Standalone verifier for a selected synthetic review ZIP. No extraction/network."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path,PurePosixPath
import stat
import sys
import zipfile

FORMAT='we-the-people.synthetic-review-bundle.v1'
MAX_TOTAL=32*1024*1024
MAX_FILE=8*1024*1024
MAX_FILES=512

def sha(raw):return hashlib.sha256(raw).hexdigest()
def state_sha(state):return sha(json.dumps(state,sort_keys=True,separators=(',',':')).encode())

def strict_json(raw):
    def pairs(values):
        result={}
        for key,value in values:
            if key in result:raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    def reject(_):raise ValueError('nonfinite JSON number')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=reject)

def number(value):
    try:return type(value) in {int,float} and math.isfinite(value)
    except OverflowError:return False

def verify_bytes(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_TOTAL:raise ValueError('archive bytes missing or too large')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos=archive.infolist();names=[i.filename for i in infos]
            if len(names)!=len(set(names)) or not 1<=len(names)<=MAX_FILES:raise ValueError('duplicate or excessive archive entries')
            if sum(i.file_size for i in infos)>MAX_TOTAL:raise ValueError('archive expands beyond limit')
            for info in infos:
                path=PurePosixPath(info.filename)
                if path.is_absolute() or str(path)!=info.filename or any(p in {'.','..'} for p in path.parts) or '\\' in info.filename or ':' in info.filename or info.is_dir():raise ValueError('unsafe archive name')
                if info.file_size>MAX_FILE or stat.S_ISLNK(info.external_attr>>16):raise ValueError('oversized or symbolic-link entry')
            if 'manifest.json' not in names:raise ValueError('manifest missing')
            manifest=strict_json(archive.read('manifest.json'))
            if not isinstance(manifest,dict) or manifest.get('format')!=FORMAT or not isinstance(manifest.get('files'),dict):raise ValueError('unsupported manifest format')
            if set(names)!={'manifest.json',*manifest['files']}:raise ValueError('unlisted or missing archive entries')
            files={}
            for name,expected in manifest['files'].items():
                content=archive.read(name)
                if len(content)!=expected['bytes'] or sha(content)!=expected['sha256']:raise ValueError('file checksum/length mismatch: '+name)
                files[name]=content
            boundary=strict_json(files['boundary.json'])
            if boundary.get('execution_authorized') is not False or boundary.get('layer_a_status')!='LEGAL_REVIEW_REQUIRED' or boundary.get('institutional_acceptance')!='NOT_ESTABLISHED':raise ValueError('fixed authority boundary altered')
            index=strict_json(files['index.json']);snapshots={}
            if len(index['snapshot_files'])!=len(set(index['snapshot_files'])) or len(index['comparison_files'])!=len(set(index['comparison_files'])):raise ValueError('duplicate index reference')
            for name in index['snapshot_files']:
                item=strict_json(files[name]);event=item['event'];key=(item['run_id'],item['sequence'])
                if key in snapshots:raise ValueError('duplicate snapshot identity')
                if event['sequence']!=item['sequence'] or state_sha(event['state'])!=item['state_sha256'] or event['state_sha256']!=item['state_sha256']:raise ValueError('snapshot state hash/sequence mismatch')
                snapshots[key]=item
            for item in snapshots.values():
                for pin in item['event']['state'].get('attachments',{}).values():
                    target=snapshots.get((pin['source_run_id'],pin['source_sequence']))
                    if not target or target['state_sha256']!=pin['state_sha256']:raise ValueError('snapshot dependency missing or mismatched')
            for name in index['comparison_files']:
                comparison=strict_json(files[name])
                if comparison['execution_authorized'] is not False or comparison['layer_a_status']!='LEGAL_REVIEW_REQUIRED' or comparison['causal_effect_estimated'] is not False:raise ValueError('comparison authority/causality boundary altered')
                for side in ('baseline','alternative'):
                    pin=comparison[side];target=snapshots.get((pin['run_id'],pin['sequence']))
                    if not target or target['state_sha256']!=pin['state_sha256']:raise ValueError('comparison snapshot reference mismatch')
                for metric in comparison['result']['timing']+comparison['result']['metrics']:
                    delta=metric['delta']
                    if delta is not None:
                        a,b=metric['baseline'],metric['alternative']
                        if not all(number(v) for v in (a,b,delta)) or delta!=b-a:raise ValueError('comparison arithmetic mismatch')
            return dict(format=FORMAT,bundle_id=manifest['bundle_id'],verified_files=len(files),verified_snapshots=len(snapshots),
                        verified_comparisons=len(index['comparison_files']),execution_authorized=False,layer_a_status='LEGAL_REVIEW_REQUIRED',
                        verification_scope='Checksums, safe names, references, snapshot state hashes and saved arithmetic only; not authenticity, actual outcomes, legal approval or institutional acceptance.')
    except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,json.JSONDecodeError,AttributeError,IndexError,OverflowError,RecursionError,RuntimeError) as error:
        raise ValueError('invalid review archive: '+str(error)) from error

def main(argv=None):
    parser=argparse.ArgumentParser(description='Verify a synthetic review bundle without extracting files')
    parser.add_argument('archive',type=Path);args=parser.parse_args(argv)
    try:
        if args.archive.stat().st_size>MAX_TOTAL:raise ValueError('archive too large')
        print(json.dumps(verify_bytes(args.archive.read_bytes()),indent=2));return 0
    except (ValueError,OSError) as error:
        print('INVALID: '+str(error),file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
