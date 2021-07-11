from lib.controllers import Controller
from lib.arguments import get_arguments
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    arguments = get_arguments()
    controller = Controller(
        arguments=arguments
    )
    print("All workers are running!")
    try:
        controller.join_workers()
    except KeyboardInterrupt:
        pass