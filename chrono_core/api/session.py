from ..adapters.comfyui import ComfyUIAdapter
from ..inspector.inspector import Inspector
from ..io import WorkflowLoader
from ..history import HistoryManager
from ..storage import JsonHistoryStore


class Session:
    """
    Публичная точка входа в ChronoCore.

    Session строит граф, запускает анализ
    и хранит готовый отчёт.
    """

    def __init__(self, workflow):

        self.graph = ComfyUIAdapter.from_prompt(
            workflow
        )

        self.inspector = Inspector()

        self.report = self.inspector.inspect(
            self.graph
        )

        self.history = HistoryManager()

        self.history.add(
            self.report
        )
        
    @property
    def prompts(self):
        return self.report["prompts"]


    @property
    def model(self):
        return self.report["model"]


    @property
    def sampler(self):
        return self.report["sampler"]


    @property
    def conditioning(self):
        return self.report["conditioning"]


    @property
    def loras(self):
        return self.report.get(
            "loras",
            []
        ) 

    @property
    def dependencies(self):

        return self.report.get(
            "dependencies",
            {}
        )

    @classmethod
    def from_file(cls, path):

        workflow = WorkflowLoader.load(path)

        return cls(workflow)        
        
    def save_history(
        self,
        path,
    ):

        store = JsonHistoryStore(
            path
        )

        store.save(
            self.history
        )



    def load_history(
        self,
        path,
    ):

        store = JsonHistoryStore(
            path
        )

        return store.load()        