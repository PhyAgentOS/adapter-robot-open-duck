import argparse
from dataclasses import replace
from robots_open_duck.config import load_config
from robots_open_duck.sdk import OpenDuckSDK

parser = argparse.ArgumentParser(description="Read one SDK frame without enabling motor actions")
parser.add_argument("--config", help="现场 YAML 配置；也可设置 OPEN_DUCK_NODE_CONFIG")
args = parser.parse_args()
config = replace(load_config(args.config), enable_action=False)
sdk = OpenDuckSDK(config)
sdk.connect()
try:
    positions = sdk.read_positions()
    print({"backend":config.backend,"position_rad":positions})
finally: sdk.disconnect()
