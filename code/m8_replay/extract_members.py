"""Offline maintainer utility. Extract and validate the allowlisted scientific JSON records."""
from argparse import ArgumentParser
from collections import Counter
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
import json
import sys

sys.dont_write_bytecode = True
from replay import CERT, NESTED, OUTER, bindings, checked, require, sha256


def main():
    cli=ArgumentParser(description=__doc__)
    cli.add_argument("source_code",type=Path,help="The original November 10 delivery's code directory")
    cli.add_argument("destination",type=Path,help="A new staging directory for raw records and their manifest")
    args=cli.parse_args()
    code=args.source_code.resolve()
    dest=args.destination.resolve()
    require(not dest.exists(),"Destination must be new")
    require(not dest.is_relative_to(code),"Refusing to write inside the archived delivery")
    inputs,allowed=bindings(code)
    outer_bytes=checked(code/OUTER,inputs["outer_sha256"])
    with ZipFile(BytesIO(outer_bytes)) as outer:
        require(outer.namelist().count(NESTED)==1,"Nested archive binding is not unique")
        nested_bytes=outer.read(NESTED)
        require(sha256(nested_bytes).hexdigest()==inputs["nested_sha256"],"Nested archive SHA-256 mismatch")
        payloads={}
        with ZipFile(BytesIO(nested_bytes)) as nested:
            archives={"outer":outer,"nested":nested}
            names={name:Counter(z.namelist()) for name,z in archives.items()}
            records=[]
            for (container,member),item in sorted(allowed.items()):
                require(names[container][member]==1,"Nonunique ZIP member: "+member)
                raw=archives[container].read(member)
                require(sha256(raw).hexdigest()==item["sha256"], "Archive member SHA-256: "+member)
                require(checked(code/CERT/item["file"],item["sha256"])==raw, "Frozen input differs from original bytes")
                payloads[item["file"]]=raw
                records.append(dict(**item,bytes=len(raw)))
    manifest=dict(format="m8-scientific-members-v1", outer_member=OUTER,outer_sha256=inputs["outer_sha256"],
                  nested_member=NESTED,nested_sha256=inputs["nested_sha256"],
                  validation="Original containers and selected raw JSON bytes checked during extraction.",
                  members=records)
    dest.mkdir(parents=True)
    for path,raw in payloads.items():
        target=dest/CERT/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
    (dest/"members.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(f"Extracted {len(records)} original member records into {len(payloads)} files, "
          f"{sum(map(len,payloads.values())):,} payload bytes. All match the delivered frozen copies.")

if __name__=="__main__":
    main()

