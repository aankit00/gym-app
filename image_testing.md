## TEST AGENT PROMPT – IMAGE INTEGRATION RULES ##
- Always use base64-encoded images (or real JPEG/PNG files) for all tests.
- Accepted formats: JPEG, PNG, WEBP only. No SVG/BMP/HEIC.
- Do not upload blank, solid-color, or uniform-variance images; use real photos with edges/textures.
- Re-detect MIME after transformations. Extract first frame for animated images. Resize large images.
