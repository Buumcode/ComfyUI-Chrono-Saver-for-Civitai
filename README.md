# ComfyUI-Chrono-Saver-for-Civitai

> **Native ComfyUI workflow metadata + native Civitai resources metadata.**

Main goal was to save ComfyUI-generated image with embedded workflow metadata and include auto-detected Civitai resources metadata. 

---

## Features

* Automatic workflow analysis
* Automatic prompt extraction
* Automatic checkpoint detection
* Automatic LoRA detection
* Automatic embedding detection
* Automatic Civitai metadata generation
* Native ComfyUI workflow preservation
* Easy Remix compatible
* Automatic filename variables
* PNG / JPEG / WebP support

* Automatic Civitai AIR/resource detection
* Inject Civitai AIR/resources metadata in file metadata
* Allow Civitai to automatically recognize models and LoRAs

![Chrono Saver for Civitai](https://github.com/user-attachments/assets/c88dc40a-7ead-4e90-9bef-ccf9ac13d2cd)

---
## Installation

Use ComfyUI Manager to install. Or install manually:

1. Open your ComfyUI `custom_nodes` directory.
2. Clone this repository:

   ```bash
   git clone https://github.com/Buumcode/ComfyUI-Chrono-Saver-for-Civitai.git
   ```
3. Install dependencies:
   ```bash
   pip install -r ComfyUI-Chrono-Saver-for-Civitai/requirements.txt   
   ```
Restart ComfyUI.   

---
## License

MIT License
