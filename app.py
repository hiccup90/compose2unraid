from flask import Flask, render_template, request
import yaml
import xml.etree.ElementTree as ET
from xml.dom import minidom

app = Flask(__name__)

def translate_to_xml(compose_text):
    data = yaml.safe_load(compose_text)
    # 获取第一个 service
    service_name = list(data['services'].keys())[0]
    service = data['services'][service_name]

    root = ET.Element("Container")
    ET.SubElement(root, "Name").text = service_name
    ET.SubElement(root, "Repository").text = service.get('image', '')
    ET.SubElement(root, "Network").text = "bridge"
    
    # 路径映射逻辑
    for vol in service.get('volumes', []):
        if isinstance(vol, str) and ':' in vol:
            host, container = vol.split(':')[:2]
            host_path = host.replace('./', f'/mnt/user/appdata/{service_name}/')
            cfg = ET.SubElement(root, "Config", {"Name": "Host Path", "Target": container, "Type": "Path"})
            cfg.text = host_path

    # 端口映射逻辑
    for port in service.get('ports', []):
        if isinstance(port, str) and ':' in port:
            h_p, c_p = port.split(':')[:2]
            cfg = ET.SubElement(root, "Config", {"Name": "Host Port", "Target": c_p, "Type": "Port"})
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
