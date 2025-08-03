import logging
import json
from typing import Any
import uuid

import httpx

from .default_workflow import *


class ComfyUI:
    """A class encapsulating a connection to a ComfyUI API and a specific workflow.
    ```
    client = ComfyUI()  # Default workflow
    client.positive = "A great dane."  # Change the positive prompt.
    prompt_id = client.submit_job()  # Submit the job
    time.sleep(30)
    status = client.query_job(prompt_id)
    status["status"]["completed"] == True
    status["status"]["status_str"] == "success"
    outputs = client.get_job_outputs(status)
    len(outputs) == 1
    print(outputs[0][:3])
    # → ('output', '', 'ComfyUI_00001_.png')
    png_data = outputs[0][3]
    with open("dog.png","wb") as f:
        f.write(png_data)
    ```
    """

    def __init__(
        self,
    ) -> None:
        logging.debug(f"ComfyUI.__init__(): ENTRY")
        self.workflow = json.loads(DEFAULT_WORKFLOW_TEXT)
        self.endpoint = "http://127.0.0.1:8188/"

    @property
    def width(self) -> int:
        return self.workflow[EMPTY_INDEX]["inputs"]["width"]

    @width.setter
    def width(self, value: int) -> None:
        if value > 0:
            self.workflow[EMPTY_INDEX]["inputs"]["width"] = value
        else:
            raise ValueError(f"ComfyUI: width must be positive: {value=}")

    @property
    def height(self) -> int:
        return self.workflow[EMPTY_INDEX]["inputs"]["height"]

    @height.setter
    def height(self, value: int) -> None:
        if value > 0:
            self.workflow[EMPTY_INDEX]["inputs"]["height"] = value
        else:
            raise ValueError(f"ComfyUI: height must be positive: {value=}")

    @property
    def seed(self) -> int:
        return self.workflow[KSAMPLER_INDEX]["inputs"]["seed"]

    @seed.setter
    def seed(self, value: int):
        if value > 0:
            self.workflow[KSAMPLER_INDEX]["inputs"]["seed"] = value
        else:
            raise ValueError(f"ComfyUI: seed must be positive: {value=}")

    @property
    def positive(self) -> str:
        return self.workflow[POSITIVE_PROMPT_INDEX]["inputs"]["text"]

    @positive.setter
    def positive(self, value: str):
        if value.strip():
            self.workflow[POSITIVE_PROMPT_INDEX]["inputs"]["text"] = value
        else:
            raise ValueError(f"ComfyUI: positive prompt must have content")

    @property
    def negative(self) -> str:
        return self.workflow[NEGATIVE_PROMPT_INDEX]["inputs"]["text"]

    @negative.setter
    def negative(self, value: str):
        self.workflow[NEGATIVE_PROMPT_INDEX]["inputs"]["text"] = value

    def submit_job(self) -> str:
        """Submits the current workflow to create an image.
        Returns the ID (prompt_id) of the request for later queries.
        """
        logging.debug(f"ComfyUI.submit_job(): ENTRY")
        client_id = str(uuid.uuid4())
        logging.debug(f"ComfyUI.submit_job(): {client_id=}")
        job = {
            "prompt": self.workflow,
            "client_id": client_id,
        }
        response = httpx.post(
            url=f"{self.endpoint}prompt",
            json=job,
        )
        logging.debug(
            f"ComfyUI.submit_job(): {response.status_code=}: {response.text=}"
        )
        response.raise_for_status()
        response_data = response.json()
        logging.debug(f"ComfyUI.submit_job(): {response_data=}")
        prompt_id = response_data.get("prompt_id", "")
        if not prompt_id:
            logging.warning(
                f"ComfyUI.submit_job(): Allegedly successful submission but no prompt_id returned: {response.status_code=}"
            )
        logging.debug(
            f"ComfyUI.submit_job(): EXIT: {client_id=}: {response.status_code=}: {prompt_id=}"
        )
        return prompt_id

    def query_job(
        self,
        prompt_id: str,
    ) -> dict[str, Any]:
        """Fetches the history of a job identified by prompt_id.
        You can pass the output of this method directly to the get_job_output() method
        to download the results once the object reports successful completion.
        """
        logging.debug(f"ComfyUI.query_job(): ENTRY: {prompt_id=}")
        response = httpx.get(
            url=f"{self.endpoint}history/{prompt_id}",
        )
        logging.debug(f"ComfyUI.query_job(): {response.status_code=}\t{response.text=}")
        response.raise_for_status()
        history = response.json()
        logging.debug(f"ComfyUI.query_job(): {history.keys()=}")
        if prompt_id in history:
            return history[prompt_id]
        else:
            logging.debug(
                f"ComfyUI.query_job(): prompt_id not in returned dictionary: {prompt_id=}: {history.keys()}"
            )
            raise KeyError("prompt_id not found: {prompt_id=}")
        logging.debug(f"ComfyUI.query_job(): EXIT: {prompt_id=}")

    def download_output(
        self,
        filename: str,
        subfolder: str = "",
        folder_type: str = "output",
    ) -> bytes:
        """Gets the output file (PNG image) for a specific file."""
        logging.debug(
            f"ComfyUI.download_output(): ENTRY: {folder_type}/{subfolder}/{filename=}"
        )
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        response = httpx.get(
            url=f"{self.endpoint}view",
            params=params,
        )
        logging.debug(f"ComfyUI.download_output(): {response.status_code=}")
        response.raise_for_status()
        data = response.read()
        logging.debug(f"ComfyUI.download_output(): EXIT: {len(data)=}")
        return data

    def get_job_outputs(
        self,
        history: dict[str, Any],
    ) -> list[tuple[str, str, str, bytes]]:
        """Pull out all the images referenced in a history dictionary as obtained from self.query_job()
        Returns a list of tuples:
            folder_type: Typically "output"
            subfolder: Typically ""
            filename: e.g. "ComfyUI_00014_.png"
            image: bytes of the corresponding PNG image
        """
        if "outputs" not in history:
            raise ValueError(
                f"ComfyUI.get_job_outputs(): 'outputs' key not found in history."
            )

        image_dicts: list[dict[str, str]] = []
        for key in history["outputs"]:
            logging.debug(f"ComfyUI.get_job_outputs(): history[outputs]: {key=}")
            if "images" in history["outputs"][key]:
                image_dicts += history["outputs"][key]["images"]
            else:
                logging.warning(
                    f"ComfyUI.get_job_outputs(): 'images' key not found in history[outputs] dictionary: {key=}"
                )

        output_data: list[tuple[str, str, str, bytes]] = []
        for image_dict in image_dicts:
            try:
                filename = image_dict["filename"]
                subfolder = image_dict.get("subfolder", "")
                folder_type = image_dict.get("type", "output")
            except KeyError as exc:
                logging.warning(
                    f"ComfyUI.get_job_outputs(): 'filename' key not found in images dictionary: {exc}"
                )
                continue
            data = self.download_output(filename, subfolder, folder_type)
            output_data.append((folder_type, subfolder, filename, data))
        logging.debug(f"ComfyUI.get_job_outputs(): {len(output_data)=}")
        return output_data
