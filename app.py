import os
import yaml
import xml.etree.ElementTree as ET
from xml.dom import minidom
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Unraid 模板存放路径 (对应容器内映射路径 /templates)
TEMPLATE_DIR = "/templates"

def translate_to_xml(compose_text):
    data = yaml.safe_load(compose_text)
    if not data or 'services' not in data:
        raise ValueError("无效的 Compose 内容：未发现 services 字段")
        
    # 获取第一个 service
    service_name = list(data['services'].keys())[0]
    service = data['services'][service_name]

    # 创建 XML 根节点
    root = ET.Element("Container", {"version": "2"})
    ET.SubElement(root, "Name").text = str(service_name)
    ET.SubElement(root, "Repository").text = str(service.get('image', ''))
    ET.SubElement(root, "Registry").text = "https://hub.docker.com/"
    ET.SubElement(root, "Network").text = str(service.get('network_mode', 'bridge'))
    ET.SubElement(root, "Privileged").text = "true" if service.get('privileged') else "false"
    
    # --- 基础元数据 (补全以防占位符) ---
    ET.SubElement(root, "Support").text = ""
    ET.SubElement(root, "Project").text = ""
    ET.SubElement(root, "Overview").text = f"Container {service_name} converted from Docker Compose."
    ET.SubElement(root, "Category").text = "Tools:"
    ET.SubElement(root, "Icon").text = "" # 你可以在此填入你的圆角矩形图标链接

    # --- WebUI 逻辑 ---
    ports_list = service.get('ports', [])
    if ports_list and isinstance(ports_list[0], str):
        # 提取第一个端口映射的主机端口
        host_port = ports_list[0].split(':')[0]
        ET.SubElement(root, "WebUI").text = f"http://[IP]:{host_port}"
    else:
        ET.SubElement(root, "WebUI").text = ""

    # --- 路径映射 (Volumes) ---
    for vol in service.get('volumes', []):
        if isinstance(vol, str) and ':' in vol:
            parts = vol.split(':')
            host_path = parts[0].replace('./', f'/mnt/user/appdata/{service_name}/')
            container_path = parts[1]
            
            cfg = ET.SubElement(root, "Config", {
                "Name": "Host Path", "Target": container_path, "Default": "",
                "Mode": "rw", "Description": "Container Path: " + container_path,
                "Type": "Path", "Display": "always", "Required": "false", "Mask": "false"
            })
            cfg.text = host_path

    # --- 端口映射 (Ports) ---
    for port in ports_list:
        if isinstance(port, str) and ':' in port:
            h_p, c_p = port.split(':')[:2]
            cfg = ET.SubElement(root, "Config", {
                "Name": "Host Port", "Target": c_p, "Default": "",
                "Mode": "tcp", "Description": "Container Port: " + c_p,
                "Type": "Port", "Display": "always", "Required": "false", "Mask": "false"
            })
            cfg.text = h_p

    # --- 环境变量 (Environment) 增强版逻辑 ---
    env = service.get('environment', {})
    env_configs = []

    if isinstance(env, dict):
        for k, v in env.items():
            env_configs.append({'key': k, 'value': v})
    elif isinstance(env, list):
        for item in env:
            if isinstance(item, str) and '=' in item:
                k, v = item.split('=', 1)
                env_configs.append({'key': k, 'value': v})

    for item in env_configs:
        cfg = ET.SubElement(root, "Config", {
            "Name": str(item['key']), "Target": str(item['key']), "Default": "",
            "Mode": "", "Description": f"Variable: {item['key']}",
            "Type": "Variable", "Display": "always", "Required": "false", "Mask": "false"
        })
        cfg.text = str(item['value'])

    # 美化 XML 输出
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
            return jsonify({"success": False, "error": f"容器内路径 {TEMPLATE_DIR} 未挂载，请检查 Unraid 配置"})
        
        file_path = os.path.join(TEMPLATE_DIR, f"my-{name}.xml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_data)
        return jsonify({"success": True, "path": file_path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
