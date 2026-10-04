import json
import os
import shutil

# Make a clean web directory for chapter 1 inspection
inspect_dir = '/home/ubuntu/vagdhenu/demo/static/ch1_inspection'
os.makedirs(inspect_dir, exist_ok=True)

with open('/home/ubuntu/vagdhenu/prabhupada_training/ch1_slice_records.json') as f:
    slices = json.load(f)

# Copy all slices to web directory if not copied
for s in slices:
    dst = os.path.join(inspect_dir, s['filename'])
    if not os.path.exists(dst):
        shutil.copy(s['path'], dst)

# Generate HTML page
html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Chapter 1 Gold Slices Verification (101 Slices)</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 24px; }
        h1 { color: #38bdf8; }
        .summary { background: #1e293b; padding: 16px; border-radius: 8px; margin-bottom: 24px; border: 1px solid #334155; }
        table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; }
        th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; font-size: 14px; }
        th { background: #0284c7; color: white; }
        tr:hover { background: #334155; }
        audio { height: 32px; vertical-align: middle; }
        .dur { color: #fbbf24; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Srila Prabhupada - Chapter 1 Complete Gold Verification</h1>
    <div class="summary">
        <p><strong>Total Slices:</strong> 101 | <strong>Rule:</strong> Energy-Valley Boundary Splitting (No Syllable Clipping, No Bleed)</p>
        <p>All verses 1.1 through 1.47 + speaker introductions + ending colophon are indexed below for browser playback.</p>
    </div>
    <table>
        <thead>
            <tr>
                <th>Slice #</th>
                <th>File</th>
                <th>Duration</th>
                <th>Time Range</th>
                <th>Audio Player</th>
            </tr>
        </thead>
        <tbody>
"""

for s in slices:
    html_content += f"""            <tr>
                <td><strong>{s['index']}</strong></td>
                <td>{s['filename']}</td>
                <td class="dur">{s['duration_s']}s</td>
                <td>{s['start_s']}s &rarr; {s['end_s']}s</td>
                <td><audio controls preload="none" src="{s['filename']}"></audio></td>
            </tr>\n"""

html_content += """        </tbody>
    </table>
</body>
</html>
"""

with open(os.path.join(inspect_dir, 'index.html'), 'w') as f:
    f.write(html_content)

print(f"Generated {len(slices)} slices in {inspect_dir}/index.html")
