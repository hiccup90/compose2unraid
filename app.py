from flask import Flask, render_template, request
import yaml
import xml.etree.ElementTree as ET
from xml.dom import minidom
import datetime

app = Flask(__name__)

def translate_to_xml(compose_text):
    data = yaml.safe_load(compose_text)
    service_name = list(data['services'].keys())[0]
    service = data['services'][service_name]

    root = ET.Element("Container", {"version": "2"})
    ET.SubElement(root, "Name").text = service_name
    ET.SubElement(root, "Repository").text = service.get('image', '')
    ET.SubElement(root, "Registry").text = "https://hub.docker.com/"
    ET.SubElement(root, "Network").text = "bridge"
    ET.SubElement(root, "Shell").text = "sh"
    ET.SubElement(root, "Privileged").text = "false"
    ET.SubElement(root, "Project").text = "https://github.com/"
    ET.SubElement(root, "Category").text = "Tools: Status:Stable"
    ET.SubElement(root, "Description").text = f"Converted from Docker Compose: {service_name}"
    
    # 路径转换
    for vol in service.get('volumes', []):
        if isinstance(vol, str) and ':' in vol:
            host, container = vol.split(':')[:2]
            # 自动转换相对路径为 Unraid 标准路径
            host_path = host.replace('./', f'/mnt/user/appdata/{service_name}/')
            cfg = ET.SubElement(root, "Config", {
                "Name": "Host Path", "Target": container, "Default": "", 
                "Mode": "rw", "Description": "Path", "Type": "Path", 
                "Display": "always", "Required": "false", "Mask": "false"
            })
            cfg.text = host_path

    # 端口转换
    for port in service.get('ports', []):
        if isinstance(port, str) and ':' in port:
            h_p, c_p = port.split(':')[:2]
            cfg = ET.SubElement(root, "Config", {
                "Name": "Host Port", "Target": c_p, "Default": "", 
                "Mode": "tcp", "Description": "Port", "Type": "Port", 
                "Display": "always", "Required": "false", "Mask": "false"
            })
            cfg.text = h_p

    xml_str = ET.tostring(root, encoding='utf-8')
    return minidom.parseString(xml_str).toprettyxml(indent="  ")

@app.route('/', methods=['GET', 'POST'])
def index():
    xml_result = ""
    if request.method == 'POST':
        try:
            xml_result = translate_to_xml(request.form.get('compose_text'))
        except Exception as e:
            xml_result = f"Error: {str(e)}"
    return render_template('index.html', xml_result=xml_result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
