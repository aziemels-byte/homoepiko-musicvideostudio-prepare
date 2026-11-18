"""Source-matched storyboard grid; lyrics boundaries are editorial estimates, not fake transcriptions."""
import json
from pathlib import Path
DURATION = 183.624
# 26 approved conceptual beats, not verified word-alignment. Change as needed.
IDEAS = [
("CHORUS", "Homo Epico", "A hand-drawn street bursts from a monochrome sketch into an energetic halftone universe; every chest pop folds the road into waves."),
("CHORUS", "Too soon / zu früh", "Each locking hit bends giant painted clock faces; the city melts into vigorous purple and amber brushstrokes."),
("CHORUS", "Echo", "Sharp tutting forms trigger graphic echo silhouettes behind him, each offset in time; clean full-body focus."),
("CHORUS", "Homo Sapiens? No", "A decisive footwork sequence turns the comic street into stacked impossible illustrated architecture."),
("VERSE1", "Clock is late", "His quick heel-toe steps pull the street backward while distant clocks run in reverse."),
("VERSE1", "Tomorrow's idea", "Fluid comic-book transition through retro city, present street, and imagined future on successive arm locks."),
("VERSE1", "Noise has order", "Hands perform geometric tutting; loose ink lines assemble into precise dynamic orbit diagrams."),
("VERSE1", "New platform", "With a strong chest pop, a doodled impossible invention turns into a glossy consumer ad parody."),
("VERSE1", "Too early / too far", "A crisp pop-lock phrase rips through three painted graphic dimensions with distinct palettes."),
("VERSE1", "What's next", "Freeze pose stops the clockwork city mid-collapse, then reopens an endless tunnel made of illustrated panels."),
("CHORUS", "Homo Epico", "Energetic locking cycle. Comic panel walls stretch into spinning kaleidoscopic layers."),
("CHORUS", "Born too early", "Dance hits ripple across mirrored illustrated streets; the center dancer stays anatomically stable."),
("CHORUS", "Echo", "A sequence of stylized silhouettes imitates the dancer at delayed intervals, like a hand-drawn strobe."),
("CHORUS", "Homo Sapiens?", "He folds the comic universe into a painted globe with confident tutting angles."),
("VERSE2", "Gulliver returns", "Miniature people at a long dinner table laugh; the table unfolds into a giant geographic map under his steps."),
("VERSE2", "Tourist brochure", "Plastic airport terminals, tourist buses, and identical tourist postcard scenes assemble behind the dancer."),
("VERSE2", "Horizon's limit", "An endless tourist bus circulates a tiny postcard world while a vivid real city unfolds beyond it."),
("VERSE2", "All inclusive", "Grotesque rubber-hose vacation icons, identical pool patterns, and robotic tourists react to his precise isolations."),
("VERSE2", "Where is Starbucks?", "A ridiculous branded resort caricature gives way to richly lived-in streets and a hand-painted world."),
("VERSE2", "Everyone's Lilliput", "The tourist city physically shrinks into an animated model at his feet during a sharp locking freeze."),
("CHORUS", "Homo Epico", "Miniature world erupts into swirling ink, brushes and comic panels orbiting his full-body footwork."),
("CHORUS", "Born too early", "A massive kinetic painted city folds and unfolds with every pop and arm extension."),
("CHORUS", "Echo", "A layered crowd of graphic silhouettes repeats earlier moves with perfectly staggered visual echo trails."),
("CHORUS", "Homo Sapiens? No", "All worlds collide into a monumental layered comic illustration and freeze on a strong body lock."),
("OUTRO", "Instrumental", "Energetic dance hits trigger rhythmic fragmentation and recombination of the graphic universe."),
("OUTRO", "Instrumental ending", "The illustrated world contracts to one point as the last popping freeze holds the frame; blackout."),
]

# 136 BPM from librosa+HPSS on the supplied MP3 (estimate); max scene < 10s.
EDGES = [round(i*(60/136)*16,3) for i in range(26)] + [DURATION]
# 25*7.059=176.471, final 7.153 (valid). 26 scenes total.
assert len(EDGES)==27 and len(IDEAS)==26
assert all(0 < b-a <= 10 for a,b in zip(EDGES,EDGES[1:])),EDGES

STYLE = ("Continuous audio-reactive animated music video. Same unmistakable charismatic thin mustached male rapper, "
         "messy light brown mullet, worn dark burgundy leather jacket, dark cargo pants, white shoes. "
         "Hand-painted 2.5D rotoscope with gritty xerox print textures, expressive comic ink strokes, halftone shading, "
         "electric violet / burnt orange accents. Real skilled upright popping, locking and tutting choreography: "
         "strong chest hits, precision arm snaps, geometric isolations, dynamic footwork and sudden freezes, "
         "full-body framing, feet visible. Movement initiates the transformation of the world. "
         "Camera keeps dancer recognizable, stable face and anatomy, no head spins or body deformation, "
         "no text, no captions, no random cut, no watermark. ")

def make_plan():
    scenes = []
    for i, (sec, phrase, idea) in enumerate(IDEAS):
        a,b=EDGES[i:i+2]
        scenes.append({"id":f"S{i+1:02d}","start":a,"end":b,"duration":round(b-a,3),
                       "section":sec,"lyric_hint":phrase,"prompt":STYLE+idea,
                       "first_frame":None,
                       "status":"planned"})
    return {"title":"Homo Epiko", "duration":DURATION,"bpm_grid_estimate":136,
            "timing_warning":"Bar-grid boundaries and lyric hints are editorial drafts; do NOT claim word-level alignment. Verify against source song.",
            "scenes":scenes}
