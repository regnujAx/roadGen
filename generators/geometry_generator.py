from abc import ABC, abstractmethod


class CG_GeometryGenerator(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def add_geometry(self):
        pass