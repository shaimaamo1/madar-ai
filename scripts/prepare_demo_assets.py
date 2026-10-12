"""Developer-only encoding of original generated images; no runtime dependencies added.

Use a development Python with Pillow, and source metadata /tmp/madar-photo-source-N.json.
Original generated PNG files are left unchanged. Never downloads listing photographs.
"""
import argparse
import hashlib
import json
from pathlib import Path

from backend.demo_inventory import LISTINGS


def prepare(sources, destination):
    from PIL import Image, ImageOps
    destination.mkdir(parents=True, exist_ok=True)
    manifest=[]
    for index,listing in enumerate(LISTINGS,1):
        metadata=json.loads((sources/f'madar-photo-source-{index}.json').read_text())
        source=Path(metadata['path'])
        with Image.open(source) as original:
            image=ImageOps.exif_transpose(original).convert('RGB')
            image.thumbnail((1024, 768), Image.Resampling.LANCZOS)
            target=destination/f'property-{index:02}.webp'
            image.save(target,format='WEBP',quality=83,method=6)
            manifest.append({'reference':f'DEMO-EG-{index:03}','title':listing[0],'property_type':listing[2],
                             'file':target.name,'width':image.width,'height':image.height,'bytes':target.stat().st_size,
                             'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                             'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                             'source':'Original OpenAI image generation output',
                             'illustrative':True,'verified_property_photograph':False,'scene':metadata['scene']})
    assert len({x['sha256'] for x in manifest})==30, 'Images must be distinct'
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent.parent/'backend/demo_assets')
    args=parser.parse_args()
    result=prepare(args.sources,args.output)
    print(f'Prepared {len(result)} distinct optimized images ({sum(x["bytes"] for x in result)} bytes total).')
