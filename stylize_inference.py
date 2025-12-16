import torch
from torchvision import transforms
from transformer_net import TransformerNet, TransformerNetNC8
from PIL import Image
import os

# Disable oneDNN to avoid "could not create a primitive" error
os.environ["ONEDNN_VERBOSE"] = "0"
torch.backends.mkldnn.enabled = False



def load_image(filename, size=None, scale=None, max_size=512):
    img = Image.open(filename).convert('RGB')
    
    # Automatically resize large images to prevent memory issues
    if size is None and scale is None:
        # Resize if either dimension exceeds max_size
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
    elif size is not None:
        img = img.resize((size, size), Image.LANCZOS)
    elif scale is not None:
        img = img.resize((int(img.size[0] / scale), int(img.size[1] / scale)), Image.LANCZOS)
    return img


def save_image(filename, data):
    img = data.clone().clamp(0, 255).numpy()
    img = img.transpose(1, 2, 0).astype("uint8")
    img = Image.fromarray(img)
    img.save(filename)

def perform_inference(content_image_path, model_path, output_image_path):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    content_image = load_image(content_image_path)
    content_transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Lambda(lambda x: x.mul(255))
    ])
    content_image = content_transform(content_image)
    content_image = content_image.unsqueeze(0).to(device)

    with torch.no_grad():
        # Auto-detect architecture based on file size
        # NC8 models are ~446KB, standard models are ~6.7MB
        model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
        
        if model_size_mb < 1.0:  # NC8 architecture (old pretrained models)
            style_model = TransformerNetNC8()
        else:  # Standard architecture (new custom models)
            style_model = TransformerNet()
        
        state_dict = torch.load(model_path, map_location=device, weights_only=False)
        # remove saved deprecation warning keys using this specific loop
        for k in list(state_dict.keys()):
            if re.search(r'in\d+\.running_(mean|var)$', k):
                del state_dict[k]
        style_model.load_state_dict(state_dict)
        style_model.to(device)
        
        output = style_model(content_image).cpu()
        
    save_image(output_image_path, output[0])
    return output_image_path

# Helper to handle deprecated keys just in case, though handled inline above mostly
import re
