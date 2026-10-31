/** Read the glTF JSON chunk of a .glb file (test-only helper). */
import fs from 'node:fs';

export function readGltfJson(glbPath) {
  const buf = fs.readFileSync(glbPath);
  if (buf.readUInt32LE(0) !== 0x46546c67) throw new Error(`${glbPath}: not a GLB`);
  const jsonLength = buf.readUInt32LE(12);
  if (buf.readUInt32LE(12 + 4) !== 0x4e4f534a) throw new Error(`${glbPath}: JSON chunk missing`);
  return JSON.parse(buf.subarray(20, 20 + jsonLength).toString('utf8'));
}

export function englishStringsInGlb(gltf) {
  const labels = [];
  const descriptions = [];
  for (const node of gltf.nodes ?? []) {
    const extras = node.extras;
    if (!extras?.partId) continue;
    if (extras.label) labels.push(extras.label);
    if (extras.description) descriptions.push(extras.description);
  }
  const materials = (gltf.materials ?? []).map((m) => m.name).filter(Boolean);
  return { labels, descriptions, materials };
}
