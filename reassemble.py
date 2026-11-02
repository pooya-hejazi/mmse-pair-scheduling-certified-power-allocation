"""Reassemble the exact reviewed ZIP from the seven downloaded repository parts."""
from pathlib import Path
import hashlib,json,os

def main():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'ARCHIVE_PARTS.json').read_text(encoding='utf-8'))
    output=root/manifest['archive'];expected=manifest['sha256']
    if output.exists():
        if hashlib.sha256(output.read_bytes()).hexdigest()==expected:
            print('The reviewed archive already exists and its SHA-256 is valid.');return
        raise FileExistsError('Existing output differs; move it before reassembly.')
    temporary=output.with_suffix(output.suffix+'.assembling')
    digest=hashlib.sha256();total=0
    try:
        with temporary.open('xb') as dest:
            for row in manifest['parts']:
                part=root/row['name'];data=part.read_bytes()
                if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
                    raise ValueError('Part size or SHA-256 mismatch: '+row['name'])
                dest.write(data);digest.update(data);total+=len(data)
        if total!=manifest['bytes'] or digest.hexdigest()!=expected:
            raise ValueError('Reassembled archive hash differs from reviewed archive.')
        os.rename(temporary,output)
    except BaseException:
        if temporary.exists():temporary.unlink()
        raise
    print('Created '+output.name+'; SHA-256 verified: '+expected)

if __name__=='__main__':main()
