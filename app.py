def translate_to_xml(compose_text):
    data = yaml.safe_load(compose_text)
    service_name = list(data['services'].keys())[0]
    service = data['services'][service_name]

    root = ET.Element("Container", {"version": "2"})
    ET.SubElement(root, "Name").text = service_name
    ET.SubElement(root, "Repository").text = service.get('image', '')
    ET.SubElement(root, "Registry").text = "https://hub.docker.com/"
    ET.SubElement(root, "Network").text = "bridge"
    ET.SubElement(root, "Privileged").text = "true" if service.get('privileged') else "false"
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
            
            # 补全所有属性以消除 {2}, {4} 等占位符
            cfg = ET.SubElement(root, "Config", {
                "Name": "Host Path",
                "Target": container,
                "Default": "",           # 对应 {2}
                "Mode": "rw",
                "Description": "",       # 对应 {4}
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
                "Description": "Environment Variable",
                "Type": "Variable",
                "Display": "always",
                "Required": "false",
                "Mask": "false"
            })
            cfg.text = str(value)

    xml_str = ET.tostring(root, encoding='utf-8')
    return service_name, minidom.parseString(xml_str).toprettyxml(indent="  ")
