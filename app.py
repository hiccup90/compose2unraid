import os
import yaml
import xml.etree.ElementTree as ET
from xml.dom import minidom
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Unraid 模板存放路径
TEMPLATE_DIR = "/templates"

def translate_to_xml(compose_text):
    data = yaml.safe_load(compose_text)
    if not data or 'services' not in data:
        raise ValueError("无效的 Compose 文件：缺少 services 字段")
        
    service_name = list(data['services'].keys())[0]
    service = data['services'][service_name]

    root = ET.Element("Container", {"version": "2"})
    ET.SubElement(root, "Name").text = str(service_name)
    ET.SubElement(root, "Repository").text = str(service.get('image', ''))
    ET.SubElement(root, "Registry").text = "https://hub.docker.com/"
    ET.SubElement(root, "Network").text = "bridge"
    ET.SubElement(root, "Privileged").text = "true" if service.get('privileged') else "false"
    
    # 显式补全 Unraid 顶层标签，防止 UI 显示异常
    ET.SubElement(root, "Support").text = ""
    ET.SubElement(root, "Project").text = ""
    ET.SubElement(root, "Overview").text = ""
    ET.SubElement(root, "Category").text = "Tools:"
    ET.SubElement(root, "WebUI").text = ""
    ET.SubElement(root, "Icon").text = ""

    # 路径映射
    for vol in service.get('volumes', []):
        if isinstance(vol, str) and ':' in vol:
            host, container = vol.split(':')[:2]
            host_path = host.replace('./', f'/mnt/user/appdata/{service_name}/')
            # 补全所有属性：Default 对应 {2}, Description 对应 {4}
            cfg = ET.SubElement(root, "Config", {
                "Name": "Host Path",
                "Target": container,
                "Default": "",
                "Mode": "rw",
                "Description": "",
                "Type": "Path",
                "Display": "always",
                "Required": "false",
                "Mask": "false"
            })
            cfg.text = host_path

    # 端口映射
    for port in service.get('ports', []):
        if isinstance(port, str) and ':' in port:
            h_p, c_p = port.split(':')[:2]
            cfg = ET.SubElement(root, "Config", {
                "Name": "Host Port",
                "Target": c_p,
                "Default": "",
                "Mode": "tcp",
                "Description": "",
                "Type": "Port",
                "Display": "always",
                "Required": "false",
                "Mask": "false"
            })
            cfg.text = h_p

    # 环境变量
    env = service.get('environment', {})
    if isinstance(env, dict):
        for key, value in env.items():
            cfg = ET.SubElement(root, "Config", {
                "Name": key,
                "Target": key,
                "Default": "",
                "Mode": "",
                "Description": "Variable",
                "Type": "Variable",
                "Display": "always",
                "Required": "false",
                "Mask": "false"
            })
            cfg.text = str(value)

    xml_str = ET.tostring(root, encoding='utf-8')
    return service_name, minidom.parseString(xml_str).toprettyxml(indent="  ")

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    try:
        content = request.json.get('compose_text')
        name, xml_data = translate_to_xml(content)
        return jsonify({"success": True, "name": name, "xml": xml_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/save', methods=['POST'])
def save():
    try:
        name = request.json.get('name')
        xml_data = request.json.get('xml')
        if not os.path.exists(TEMPLATE_DIR):
            return jsonify({"success": False, "error": f"容器内路径 {TEMPLATE_DIR} 不存在，请检查 Docker 映射"})
        
        file_path = os.path.join(TEMPLATE_DIR, f"my-{name}.xml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_data)
        return jsonify({"success": True, "path": file_path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
