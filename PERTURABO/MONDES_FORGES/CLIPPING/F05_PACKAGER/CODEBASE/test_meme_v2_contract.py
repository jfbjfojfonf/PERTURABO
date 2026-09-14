import importlib.util
from pathlib import Path

root = Path('/home/ubuntu/perturabo_work/MONDES_FORGES/CLIPPING')
path = root / 'F05_PACKAGER/CODEBASE/packager.py'
spec = importlib.util.spec_from_file_location('packager', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cfg = {
    'source_post': {
        'text': 'internal source copy must not export',
        'screenshot_png': 'ARCHIVUM/campaign/source.png',
        'url': 'https://example.invalid/post',
        'author': '@source',
        'credit_display': 'Source: @source'
    },
    'operator_bindings': {
        'A01': {'clip_id': 'meme_clip_01', 'meme_tag': 'M1', 'channel_id': 'channel_us_01'}
    }
}
payload = {
    'title': 'Source Reaction',
    'tweet': {'text': 'Original reaction text', 'keywords_style': {'red': ['reaction']}},
    'reaction_tweet': 'Original reaction text',
    'text_emotion': 'Students seeing this:',
    'emotion': 'incredulous',
    'duration_sec': 8,
    'metadata': {'title': 'Source Reaction', 'description': 'A reaction.', 'tags': ['#meme']}
}
asset = mod._logo_video_asset({'angle_id': 'A01'}, payload, 'meme_v2', {}, 1, meme='M1', meme_v2=cfg)
assert asset['clip_id'] == 'meme_clip_01'
assert asset['meme_tag'] == 'M1'
assert asset['channel_id'] == 'channel_us_01'
assert asset['source_post']['screenshot_png'].endswith('source.png')
assert 'text' not in asset['source_post']
assert asset['reaction_tweet'] == 'Original reaction text'
exported = mod._meme_v2_export_block(cfg)
assert 'text' not in exported['source_post']
print('MEME_V2_CONTRACT_TEST_OK')
