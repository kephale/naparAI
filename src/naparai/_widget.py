"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""
import os
from threading import Thread
from typing import TYPE_CHECKING

import openai
from dotenv import load_dotenv
from qtpy import Qsci
from qtpy.QtWidgets import (
    QComboBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    import napari

load_dotenv()  # take environment variables from .env.
openai.api_key = os.getenv("OPENAI_API_KEY")


class NaparAIEditor(Qsci.QsciScintilla):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        # self.setLexer(Qsci.QsciLexerPython(self))
        self.setLexer(Qsci.QsciLexerMarkdown(self))
        self.setText(text)
        self.setWrapMode(1)


class NaparAIPythonEditor(Qsci.QsciScintilla):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setLexer(Qsci.QsciLexerPython(self))
        # self.setLexer(Qsci.QsciLexerMarkdown(self))
        self.setText(text)
        self.setWrapMode(1)


class NapariAIWidget(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer

        # Prompt worker
        self.worker = None
        # Python eval worker
        self.eval_worker = None

        btn = QPushButton("Send request")
        btn.clicked.connect(self._on_click)

        self.setLayout(QVBoxLayout())

        self.txt = NaparAIEditor("")

        # Text area for the user to enter prompts
        self.input_area = QTextEdit("")

        # Model dropdown
        self.ai_selection = QComboBox()
        self.ai_selection.addItem("gpt-3.5-turbo")
        self.ai_selection.addItem("gpt-4")

        # Sync napari state with AI
        sync_btn = QPushButton("Create a sync prompt")
        sync_btn.clicked.connect(self._sync_state)

        self.eval_area = NaparAIPythonEditor("")

        # Evaluate button
        eval_btn = QPushButton("Run code")
        eval_btn.clicked.connect(self._eval_text)

        self.layout().addWidget(self.ai_selection)
        self.layout().addWidget(self.txt)
        self.layout().addWidget(self.input_area)
        self.layout().addWidget(sync_btn)
        self.layout().addWidget(btn)
        self.layout().addWidget(self.eval_area)
        self.layout().addWidget(eval_btn)

    def eval_prompt(self, model, prompt):
        completion = openai.ChatCompletion.create(
            model=model, messages=[{"role": "user", "content": prompt}]
        )
        response = completion.choices[0].message.content

        new_history = f"{self.txt.text()}\n### User\n{prompt}\n\n### AI({model})\n{response}\n\n"

        self.txt.setText(new_history)

        self.worker = None

    def _on_click(self):
        prompt = self.input_area.toPlainText()

        self.send_prompt(prompt)

    def eval_python(self, code):
        exec(code)

    def _eval_text(self):
        to_eval = self.eval_area.text()

        self.eval_python(to_eval)

        # Non-blocking has issues because some things should only be done in main thread
        # if not self.worker:
        #     args = (to_eval,)
        #     self.eval_worker = Thread(target=self.eval_python, args=args)
        #     self.eval_worker.start()
        # else:
        #     print("There currently is a prompt being evaluated. Please wait and try again.")

    def _sync_state(self):
        prompt = "The Python-based image visualization tool napari is already running and has the following state.\n"

        # Layers
        prompt += f"There are {len(self.viewer.layers)} layers open.\n"
        for idx, layer in enumerate(self.viewer.layers):
            prompt += f"There is a layer named {layer.name} that contains data of type {type(layer.data)} with shape {layer.data.shape} and dtype of {layer.data.dtype}.\n"

        # Environment and libraries
        prompt += "The Python libraries numpy, dask, pytorch, and scikit-image are already installed. Only use known pytorch models, like stardist, and cellpose.\n"
        # For stardist use the '3D_demo' model for 3D data.\n"

        # Advice to fix some bugs with napari code that gets generated
        # - When writing scripts do not include import statements
        prompt += "Assume that the napari viewer is called 'viewer', assume napari is already running, do not use the colormap keyword when adding labels, and use viewer.layers when referencing open layers.."

        # Plugins

        self.input_area.setText(prompt)

        # self.send_prompt(prompt)

    def send_prompt(self, prompt):
        if not self.worker:
            args = (self.ai_selection.currentText(), prompt)
            self.worker = Thread(target=self.eval_prompt, args=args)
            self.worker.start()
        else:
            print(
                "There currently is a prompt being evaluated. Please wait and try again."
            )


"""
Check out QTConsole
https://github.com/jupyter/qtconsole/blob/729a87a3e6e8d63da22b82bcc3b7d60b6cabee29/qtconsole/jupyter_widget.py#L53

Also check out https://github.com/pyqtconsole/pyqtconsole/blob/master/pyqtconsole/console.py
- PythonConsole
"""

if __name__ == "__main__":
    import napari

    viewer = napari.Viewer()

    widget = NapariAIWidget(viewer)

    viewer.window.add_dock_widget(widget, name="napariAI")

    # napari.run()
