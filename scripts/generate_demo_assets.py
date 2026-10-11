"""Original SVG architectural illustrations, dedicated to CC0. No external images."""
from html import escape
from pathlib import Path
from backend.demo_inventory import LISTINGS

DEST = Path(__file__).resolve().parent.parent / 'backend/demo_assets'


def render(index, listing):
    title, location, kind, *_ = listing
    sky=['#ebeee7','#eee9df','#e5eef0','#eae5e0'][index%4]
    facade=['#e9ded0','#ebe7de','#d7ddd8','#e5d2bd'][index%4]
    floors={'Apartment':4,'Villa':2,'Duplex':3,'Penthouse':4,'Office':5,'Commercial':2}[kind]
    top=330-floors*47
    panels=[]
    for floor in range(floors):
        for col in range(5):
            x=238+col*61;y=top+18+floor*47
            panels.append(f'<rect x="{x}" y="{y}" width="42" height="30" rx="2" fill="url(#glass)"/><path d="M{x+21} {y}v30 M{x} {y+15}h42" stroke="#ffffff55" stroke-width="1"/>')
        if kind not in ('Office','Commercial'):
            panels.append(f'<path d="M220 {top+55+floor*47}h350" stroke="#afa393" stroke-width="6"/><path d="M225 {top+44+floor*47}h340" stroke="#193b5744" stroke-width="2"/>')
    trees=''.join(f'<path d="M{x} 362v-58" stroke="#85735d" stroke-width="6"/><ellipse cx="{x}" cy="292" rx="{22+(index+i)%9}" ry="40" fill="{color}"/><ellipse cx="{x-10}" cy="305" rx="18" ry="24" fill="#5d8873"/>' for i,(x,color) in enumerate([(137,'#365e50'),(688,'#365e50'),(96,'#4d7864')]))
    terrace='<path d="M216 '+str(top-5)+'h356v-22H216z" fill="#9eaa98"/><path d="M235 '+str(top-28)+'h145v-20H235z" fill="#e9e2d7"/>' if kind=='Penthouse' else ''
    shop='<rect x="235" y="281" width="324" height="51" rx="2" fill="url(#glass)"/><path d="M343 281v51 M451 281v51" stroke="#e5dfd6" stroke-width="7"/>' if kind=='Commercial' else ''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="520" viewBox="0 0 800 520" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)} — original fictional architectural illustration</title><desc id="desc">Synthetic vector illustration for DEMO-EG-{index+1:03}. Not a photograph or verified listing. CC0.</desc>
<defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="{sky}"/><stop offset="1" stop-color="#f6f2ea"/></linearGradient><linearGradient id="glass" x2="1" y2="1"><stop stop-color="#193b57"/><stop offset=".52" stop-color="#638e9b"/><stop offset="1" stop-color="#a9bbc0"/></linearGradient><linearGradient id="pool" x2="1" y2="1"><stop stop-color="#247f86"/><stop offset="1" stop-color="#82b8b2"/></linearGradient><filter id="shadow"><feGaussianBlur stdDeviation="12"/></filter></defs>
<rect width="800" height="520" fill="url(#sky)"/><circle cx="658" cy="80" r="48" fill="#ead9b0" opacity=".6"/>
<path d="M0 298L105 277 197 291 326 264 505 281 675 266 800 287V440H0Z" fill="#c5d0c1"/><path d="M0 361Q350 322 800 351V520H0Z" fill="#a8b99d"/>
<path d="M176 405L562 383 700 445 316 474Z" fill="#101e3133" filter="url(#shadow)"/>
<path d="M217 {top}L571 {top} 641 {top+28}V354H571L217 332Z" fill="#c9bca9"/>
<path d="M571 {top}L641 {top+28}V354L571 332Z" fill="#b8ad9c"/><rect x="217" y="{top}" width="354" height="{335-top}" fill="{facade}"/>
<path d="M213 {top}L568 {top} 640 {top+26}H282Z" fill="#f4ede2"/><path d="M571 {top+6}V333" stroke="#bda987" stroke-width="4"/>
{''.join(panels)}{terrace}{shop}
<rect x="362" y="302" width="65" height="57" rx="3" fill="#193b57"/><path d="M395 302v57" stroke="#d8be83" stroke-width="2"/>
<path d="M211 357H583L654 380H265Z" fill="#ded5c7"/><path d="M292 379H610L744 520H355Z" fill="#e9e0d2"/><path d="M400 394L486 493 M460 394L570 498 M315 419H646 M336 458H686" stroke="#d0c3ae" stroke-width="2"/>
<path d="M89 387H227L302 433H151Z" fill="#f1e9da"/><path d="M101 394H222L280 427H153Z" fill="url(#pool)"/><path d="M125 399H213 M143 411H236" stroke="#c2e0da" stroke-width="2" opacity=".7"/>
{trees}<path d="M525 379h116l27 19H544Z" fill="#476d59"/><path d="M57 453Q156 404 238 457" fill="none" stroke="#608169" stroke-width="22"/>
<rect x="30" y="25" width="208" height="29" rx="14" fill="#101e31"/><text x="44" y="44" font-family="sans-serif" font-size="11" letter-spacing="1.2" fill="#d8be83">DEMO · ORIGINAL ILLUSTRATION</text>
<rect x="0" y="472" width="800" height="48" fill="#101e31"/><text x="30" y="501" font-family="sans-serif" font-size="14" fill="#f7f2e8">{escape(location)} · {escape(kind)}</text><text x="770" y="501" text-anchor="end" font-family="sans-serif" font-size="12" fill="#d8be83">DEMO-EG-{index+1:03}</text></svg>\n'''


def main():
    DEST.mkdir(exist_ok=True)
    for index,listing in enumerate(LISTINGS):
        (DEST/f'property-{index+1:02}.svg').write_text(render(index,listing))


if __name__=='__main__':main()
