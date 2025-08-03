import logging
import time
from comfyui import ComfyUI

RETRIES = [
    10,
    10,
    20,
    30,
    40,
    50,
    60,
    60,
]

logging.getLogger().level = logging.DEBUG
logging.getLogger("httpcore").level = logging.WARNING
logging.getLogger("httpx").level = logging.WARNING

client = ComfyUI()  # Default workflow
client.positive = "A tiger."  # Change the positive prompt.
prompt_id = client.submit_job()  # Submit the job

for interval in RETRIES:
    time.sleep(interval)
    status = client.query_job(prompt_id)
    if status["status"]["completed"]:
        assert status["status"]["status_str"] == "success"
        outputs = client.get_job_outputs(status)
        print(outputs[0][:3])
        png_data = outputs[0][3]
        with open("tiger.png", "wb") as f:
            f.write(png_data)
        break
    else:
        print("Waiting")
