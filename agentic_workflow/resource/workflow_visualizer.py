import os
import time
import logging

logger = logging.getLogger(__name__)

def dev_draw_mermaid(wf, prefix="", sleep_time=1.0):
    """Draws a Mermaid graph and saves it in the project root."""
    # Define the directory to save the image
    project_root = os.getcwd()  # Get the current working directory
    file_name = f"{prefix}_mermaid_graph.png"
    file_path = os.path.join(project_root, file_name)

    try:
        time.sleep(sleep_time)  # Mermaid's public API seems really defensive against DDOS.
        with open(file_path, "wb") as image_file:
            image_file.write(wf.get_graph().draw_mermaid_png())
        logger.info(f"MERMAID: Graph image saved: {file_path}")
        print(f"MERMAID: Graph image saved: {file_path}")
    except Exception as e:
        logger.error(f"MERMAID: Error drawing graph: {e}")
        print(f"MERMAID: Error drawing graph: {e}")
        return