from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame


def create_placeholder_page(title_text, description_text):
    page = QWidget()
    page.setObjectName("content")

    layout = QVBoxLayout(page)
    layout.setContentsMargins(35, 28, 35, 25)

    title = QLabel(title_text)
    title.setObjectName("page_title")

    panel = QFrame()
    panel.setObjectName("panel")

    panel_layout = QVBoxLayout(panel)
    panel_layout.setContentsMargins(25, 25, 25, 25)

    description = QLabel(description_text)
    description.setObjectName("description")
    description.setWordWrap(True)

    panel_layout.addWidget(description)

    layout.addWidget(title)
    layout.addSpacing(20)
    layout.addWidget(panel)
    layout.addStretch()

    return page
