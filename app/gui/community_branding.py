from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy

from app.paths import bundled_path


COMMUNITY_LOGO_PATH = bundled_path("app", "assets", "MadeByTheCommunity_White.png")
APP_LOGO_PATH = bundled_path("app", "assets", "SC-Intel-Tool-Logo.png")


class ScaledAssetLabel(QLabel):
    def __init__(self, image_path, fallback_text, max_size=104, min_size=68, tooltip=""):
        super().__init__()
        self.original_pixmap = QPixmap(str(image_path))
        self.fallback_text = fallback_text
        self.setAlignment(Qt.AlignCenter)
        self.setToolTip(tooltip)
        self.setMinimumSize(min_size, min_size)
        self.setMaximumSize(max_size, max_size)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.update_scaled_pixmap()

    def resizeEvent(self, event):
        self.update_scaled_pixmap()
        super().resizeEvent(event)

    def sizeHint(self):
        return QSize(self.maximumWidth(), self.maximumHeight())

    def minimumSizeHint(self):
        return self.minimumSize()

    def update_scaled_pixmap(self):
        if self.original_pixmap.isNull():
            self.setText(self.fallback_text)
            return

        size = self.contentsRect().size()
        if size.width() <= 0 or size.height() <= 0:
            size = self.sizeHint()

        self.setPixmap(
            self.original_pixmap.scaled(
                size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )


class AppLogoLabel(ScaledAssetLabel):
    def __init__(self, max_size=128, min_size=82):
        super().__init__(
            APP_LOGO_PATH,
            "SC Intel Tool",
            max_size=max_size,
            min_size=min_size,
            tooltip="SC Intel Tool",
        )


class CommunityLogoLabel(ScaledAssetLabel):
    def __init__(self, max_size=104, min_size=68):
        super().__init__(
            COMMUNITY_LOGO_PATH,
            "Community",
            max_size=max_size,
            min_size=min_size,
            tooltip="Made by the community",
        )
