#!/bin/sh
# Regenerate a cycle-profile command from the current label file and run it.
python3 - "$@" <<'PY' > /tmp/_prof_cmd.sh
import sys
labels=[]
for line in open('build/big_foot.labels'):
    p=line.split()
    if len(p)>=3 and p[0]=='al':
        n=p[2].lstrip('.')
        if '@' in n or ':' in n: continue
        labels.append((int(p[1],16), n))
labels.sort()
def rng(name):
    for i,(a,n) in enumerate(labels):
        if n==name:
            for a2,n2 in labels[i+1:]:
                if a2>a: return (a,a2)
    return None
names = sys.argv[1:] or ['nmi_handler','do_split','vram_flush','player_update',
    'draw_metasprite','level_stream','draw_strip','draw_column_attr','oam_finish',
    'hud_update','camera_update','play_run','read_pads','mt_at','mt_quads',
    'probe_flags','entities_update','entities_draw','spawn_check']
args=[]
for nm in names:
    r=rng(nm)
    if r: args.append("-prof %d:%d:%s" % (r[0],r[1],nm))
print("./build/nesemu build/big_foot.nes -frames 600 -input build/in3.txt " + " ".join(args))
PY
sh /tmp/_prof_cmd.sh | head -24
