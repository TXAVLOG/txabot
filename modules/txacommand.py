import os
import importlib
import importlib.util
import sys
import logging

# Set up logging for module loader
logger = logging.getLogger("txacommand")

# Store successfully loaded commands and metadata
# Format: { 'command_name': { 'function': callable, 'name': str, 'desc': str, 'author': str, 'command': str/list, 'module_path': str } }
loaded_commands = {}
load_summary = []
success_count = 0
fail_count = 0

def load_modules():
    global success_count, fail_count
    loaded_commands.clear()
    load_summary.clear()
    success_count = 0
    fail_count = 0
    
    modules_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Traverse directories and load modules
    for root, dirs, files in os.walk(modules_dir):
        # Exclude directories we don't want to scan (like __pycache__ or cache)
        dirs[:] = [d for d in dirs if d not in ('__pycache__', 'cache')]
        
        for file in files:
            if file in ('main.py', 'index.py'):
                # Compute absolute and relative paths
                abs_file_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_file_path, os.path.dirname(modules_dir))
                module_path = rel_path.replace(os.sep, '.').replace('.py', '')
                
                try:
                    modules_config = {}
                    rel_file_path = ""
                    # Validate registry in txac.py of parent category folder
                    parts = rel_path.split(os.sep)
                    if len(parts) >= 4:  # modules/parent_dir/sub_dir/file.py
                        parent_dir = parts[1]
                        sub_dir = parts[2]
                        file_name = parts[3]
                        rel_file_path = f"{sub_dir}/{file_name}"
                        
                        parent_dir_path = os.path.join(modules_dir, parent_dir)
                        txac_file_path = os.path.join(parent_dir_path, "txac.py")
                        
                        if not os.path.exists(txac_file_path):
                            raise ValueError(f"Thiếu file cấu hình 'txac.py' tại {parent_dir_path}")
                            
                        txac_module_name = f"modules.{parent_dir}.txac"
                        try:
                            if txac_module_name in sys.modules:
                                del sys.modules[txac_module_name]
                            spec = importlib.util.spec_from_file_location(txac_module_name, txac_file_path)
                            txac_mod = importlib.util.module_from_spec(spec)
                            sys.modules[txac_module_name] = txac_mod
                            spec.loader.exec_module(txac_mod)
                        except Exception as import_err:
                            raise ValueError(f"Lỗi khi import '{txac_file_path}': {import_err}")
                            
                        if not hasattr(txac_mod, "CONFIG"):
                            raise ValueError(f"File 'txac.py' tại {parent_dir_path} không định nghĩa biến 'CONFIG'")
                            
                        txac_config = getattr(txac_mod, "CONFIG")
                        if not isinstance(txac_config, dict):
                            raise ValueError(f"Biến 'CONFIG' trong 'txac.py' tại {parent_dir_path} phải là kiểu dict")
                            
                        modules_config = txac_config.get("modules", {})
                        if rel_file_path not in modules_config:
                            raise ValueError(f"Đường dẫn file '{rel_file_path}' chưa được đăng ký trong '{txac_file_path}'")
                            
                    # Remove from sys.modules to force reload
                    if module_path in sys.modules:
                        del sys.modules[module_path]
                    
                    # Dynamic import
                    module = importlib.import_module(module_path)
                    
                    # Validate txa dictionary
                    if not hasattr(module, 'txa'):
                        raise ValueError("Thiếu biến 'txa'")
                    txa_config = getattr(module, 'txa')
                    if not isinstance(txa_config, dict):
                        raise ValueError("Biến 'txa' phải là kiểu dict")
                    
                    # Validate required fields
                    required_keys = ['name', 'desc', 'author', 'command']
                    for key in required_keys:
                        if key not in txa_config:
                            raise ValueError(f"Biến 'txa' thiếu trường '{key}'")
                    
                    # Validate txa_command function
                    if not hasattr(module, 'txa_command'):
                        raise ValueError("Thiếu hàm 'txa_command'")
                    txa_command_fn = getattr(module, 'txa_command')
                    if not callable(txa_command_fn):
                        raise ValueError("Hàm 'txa_command' không thể gọi (callable)")
                    
                    # Parse command field (allow list of strings or single string)
                    command_field = txa_config['command']
                    commands_to_register = []
                    if isinstance(command_field, list):
                        commands_to_register = [str(c).lower().strip() for c in command_field]
                    elif isinstance(command_field, str):
                        commands_to_register = [command_field.lower().strip()]
                    else:
                        raise ValueError("Trường 'command' trong 'txa' phải là kiểu string hoặc list")
                    
                    # Clean up function name dynamically
                    raw_name = txa_config['name']
                    clean_name = raw_name
                    
                    if rel_file_path and modules_config:
                        sub_cfg = modules_config.get(rel_file_path, {})
                        if isinstance(sub_cfg, dict) and "title" in sub_cfg:
                            clean_name = sub_cfg["title"]
                            
                    if clean_name.startswith("pro_"):
                        clean_name = clean_name[4:]
                    clean_name = clean_name.replace("_", " ").title()
                    
                    # Clean up description dynamically
                    raw_desc = txa_config.get('desc', '')
                    clean_desc = raw_desc
                    if clean_desc:
                        if clean_desc == f"Tính năng {raw_name}":
                            clean_desc = f"Tính năng {clean_name}"
                        elif clean_desc.startswith("Tính năng pro_"):
                            clean_desc = "Tính năng " + clean_desc[14:].replace("_", " ")
                        elif clean_desc.startswith("pro_"):
                            clean_desc = clean_desc[4:].replace("_", " ")
                        elif clean_desc == raw_name:
                            clean_desc = clean_name
                    else:
                        clean_desc = f"Tính năng {clean_name}"
                    
                    # Register commands
                    for cmd in commands_to_register:
                        loaded_commands[cmd] = {
                            'function': txa_command_fn,
                            'name': clean_name,
                            'desc': clean_desc,
                            'author': txa_config['author'],
                            'command': command_field,
                            'module_path': module_path
                        }
                    
                    success_count += 1
                    load_summary.append({
                        'module': module_path,
                        'status': 'SUCCESS',
                        'reason': None
                    })
                    
                except Exception as e:
                    fail_count += 1
                    # Capture traceback/reason cleanly
                    reason_msg = str(e)
                    load_summary.append({
                        'module': module_path,
                        'status': 'FAILED',
                        'reason': reason_msg
                    })
