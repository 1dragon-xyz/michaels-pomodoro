from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction, QImage, QPixmap
from PySide6.QtCore import Signal, QObject, Qt

class TrayIconManager(QObject):
    # Signals
    show_settings_requested = Signal()
    toggle_ghost_requested = Signal(bool)
    toggle_mute_requested = Signal(bool)
    toggle_work_log_requested = Signal(bool)
    review_logs_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create Tray Icon
        # Note: We need a valid icon path. For now we might generate a placeholder or use standard.
        # sprint 1 used a text label, here we need a pixel icon.
        self.tray_icon = QSystemTrayIcon(parent)
        
        # Try to load real icon
        import os
        icon_path = os.path.join(os.getcwd(), 'assets', 'icon.png')
        
        if os.path.exists(icon_path):
             self.normal_icon = QIcon(icon_path)
        else:
            # Fallback to generated pixel
            from PySide6.QtGui import QPixmap, QPainter, QColor
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor("#008080")) # Teal
            painter.drawEllipse(0, 0, 16, 16)
            painter.end()
            self.normal_icon = QIcon(pixmap)
            
        self.tray_icon.setIcon(self.normal_icon)
        
        # Generate Grayscale Icon
        self.grayscale_icon = self.create_grayscale_icon(self.normal_icon)
        self.tray_icon.setToolTip("TomodOrange")
        
        # Context Menu
        self.menu = QMenu()
        self.init_menu()
        self.tray_icon.setContextMenu(self.menu)
        
        self.tray_icon.show()
        
        # On click
        self.tray_icon.activated.connect(self.on_tray_activated)

    def create_grayscale_icon(self, icon):
        """Creates a grayscale version of the given QIcon."""
        pixmap = icon.pixmap(32, 32) # Get pixmap at standard size
        image = pixmap.toImage()
        grayscale_image = image.convertToFormat(QImage.Format.Format_Grayscale8)
        return QIcon(QPixmap.fromImage(grayscale_image))

    def init_menu(self):
        # Status (Disabled Action acting as label)
        # Status (Disabled Action acting as label)
        # self.status_action = QAction("25 Minutes Remaining", self.menu) # Removed per feedback
        # self.status_action.setEnabled(False)
        # self.menu.addAction(self.status_action)
        
        # self.menu.addSeparator()
        
        # Mute Toggle
        self.mute_action = QAction("Mute", self.menu)
        self.mute_action.setCheckable(True)
        self.mute_action.triggered.connect(lambda c: self.toggle_mute_requested.emit(c))
        self.menu.addAction(self.mute_action)
        
        # Work Log Toggle
        self.work_log_action = QAction("Enable Work Logs", self.menu)
        self.work_log_action.setCheckable(True)
        self.work_log_action.triggered.connect(lambda c: self.toggle_work_log_requested.emit(c))
        self.menu.addAction(self.work_log_action)
        
        # Review Logs
        self.review_action = QAction("Review Logs", self.menu)
        self.review_action.triggered.connect(self.review_logs_requested.emit)
        self.menu.addAction(self.review_action)

        # Ghost Mode Toggle
        self.ghost_action = QAction("Ghost Mode", self.menu)
        self.ghost_action.setCheckable(True)
        self.ghost_action.triggered.connect(lambda c: self.toggle_ghost_requested.emit(c))
        self.menu.addAction(self.ghost_action)
        
        self.menu.addSeparator()
        
        # Settings
        self.settings_action = QAction("Settings", self.menu)
        self.settings_action.triggered.connect(self.show_settings_requested.emit)
        self.menu.addAction(self.settings_action)
        
        self.menu.addSeparator()
        
        # Exit
        self.quit_action = QAction("Exit", self.menu)
        self.quit_action.triggered.connect(self.quit_requested.emit)
        self.menu.addAction(self.quit_action)

    def update_ghost_state(self, is_ghost):
        """Update the menu check state and tray icon if changed externally."""
        # Block signals to prevent feedback loop if needed
        self.ghost_action.blockSignals(True)
        self.ghost_action.setChecked(is_ghost)
        self.ghost_action.blockSignals(False)
        
        # Update Icon
        if is_ghost:
            self.tray_icon.setIcon(self.grayscale_icon)
            self.tray_icon.setToolTip("TomodOrange (Ghost Mode)")
        else:
            self.tray_icon.setIcon(self.normal_icon)
            self.tray_icon.setToolTip("TomodOrange")

    def update_mute_state(self, is_muted):
        """Update the menu check state if changed externally."""
        self.mute_action.blockSignals(True)
        self.mute_action.setChecked(is_muted)
        self.mute_action.blockSignals(False)

    def update_work_log_state(self, enabled):
        """Update the menu check state for work logs."""
        self.work_log_action.blockSignals(True)
        self.work_log_action.setChecked(enabled)
        self.work_log_action.blockSignals(False)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            # Left click -> could toggle settings or just bring widget to front
            self.show_settings_requested.emit()
