import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QAction
from ui.floating_widget import FloatingWidget
from ui.settings_window import SettingsWindow
from ui.log_entry_dialog import LogEntryDialog
from ui.tray_manager import TrayIconManager
from utils.startup_manager import StartupManager
from core.timer_engine import TimerEngine
from core.audio_manager import AudioManager

from ui.log_viewer_window import LogViewerWindow

def main():
    # Fix Taskbar Icon on Windows
    import ctypes
    myappid = 'michaels.pomodoro.tomodorange.1.0' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    
    # Prevent the app from quitting when the last window (Settings) is closed
    settings = SettingsWindow() # Init early to get defaults
    log_viewer = LogViewerWindow() 
    app.setQuitOnLastWindowClosed(False)
    
    # Components
    widget = FloatingWidget()
    # settings = SettingsWindow() # Already inited
    tray_manager = TrayIconManager()
    timer_engine = TimerEngine(work_minutes=settings.current_settings['work_minutes'], break_minutes=settings.current_settings['break_minutes'])
    audio_manager = AudioManager()
    
    # --- Logic connection ---
    
    # 0. Timer -> Widget (Update Time)
    timer_engine.tick.connect(widget.label.setText)
    
    # 1. Timer -> Widget (Update Visual State Work/Break)
    def handle_state_change(state):
        # Retrieve latest settings to ensure we use current colors
        current_settings = settings.get_current_settings()
        
        if state == "work":
            # Use configured Work Color
            widget.current_text_color = current_settings['work_color']
            widget.update_style(
                text_color=widget.current_text_color, 
                bg_opacity=widget.current_bg_opacity, 
                text_opacity=widget.current_text_opacity, 
                text_size=widget.current_text_size
            )
            audio_manager.stop_break_sound()
            
        elif state == "break":
            # Use configured Break Color
            widget.current_text_color = current_settings['break_color']
            widget.update_style(
                text_color=widget.current_text_color, 
                bg_opacity=widget.current_bg_opacity, 
                text_opacity=widget.current_text_opacity, 
                text_size=widget.current_text_size
            )
            audio_manager.start_break_sound()
            
    timer_engine.state_changed.connect(handle_state_change)
    
    # 1.1 Timer -> Widget (Update Mode Work/Break for Orange Style)
    timer_engine.state_changed.connect(widget.set_mode)
    
    # 1.2 Timer -> Widget (Update Progress)
    timer_engine.tick_progress.connect(widget.set_progress)
    
    # 2. Timer -> Audio (Ticks)
    def handle_tick_sound(time_str):
        # Play tick only during Work phase
        if timer_engine.current_state == "work":
            audio_manager.play_tick()
            
    timer_engine.tick.connect(handle_tick_sound)
    
    # 2.1 Timer -> Log Dialog
    from PySide6.QtCore import QTimer
    
    # Keep reference to prevent GC
    log_dialog_ref = [None]
    
    def open_log_dialog(mode="logging"):
        # Create dialog on demand to ensure fresh state/LogManager reading
        dialog = LogEntryDialog(mode=mode)
        log_dialog_ref[0] = dialog
        
        if mode == "logging":
            # Chain to Planning Dialog on save
            def open_planning():
                # Use QTimer to separate the event loops slightly or just allow one to close
                QTimer.singleShot(100, lambda: open_log_dialog(mode="planning"))
                
            dialog.accepted.connect(open_planning)
        
        dialog.show() # Non-blocking
        
    
    def open_log_dialog_wrapper(mode="logging"):
        # Check if work logging is enabled
        current_s = settings.get_current_settings()
        # Default to True if not present (though it should be via defaults)
        if not current_s.get('work_log_enabled', False) and mode == "logging":
            return

        open_log_dialog(mode)

    # Connect to wrapper instead of direct dialog
    timer_engine.work_completed.connect(lambda: open_log_dialog_wrapper("logging"))

    # 3. Settings -> Timer & Audio
    def handle_settings_change(settings_dict):
        # Visuals
        # Store current visuals for state retention
        widget.current_bg_opacity = settings_dict['bg_opacity']
        widget.current_text_opacity = settings_dict['text_opacity']
        widget.current_text_size = settings_dict['text_size']
        
        # Determine which color to apply based on CURRENT state
        if timer_engine.current_state == "work":
             widget.current_text_color = settings_dict['work_color']
        else:
             widget.current_text_color = settings_dict['break_color']

        widget.update_style(
            text_color=widget.current_text_color, 
            bg_opacity=settings_dict['bg_opacity'],
            text_opacity=settings_dict['text_opacity'],
            text_size=settings_dict['text_size']
        )
        
        # Orange Style Updates
        widget.set_timer_style(settings_dict.get('timer_style', 'orange'))
        widget.set_orange_opacity(settings_dict.get('orange_opacity', 1.0))
        
        # Timer Durations - Fix: Only update if changed to avoid reset
        # Check if values differ from current engine values (converted to minutes)
        current_work_min = int(timer_engine.work_seconds / 60)
        current_break_min = int(timer_engine.break_seconds / 60)
        
        if (settings_dict['work_minutes'] != current_work_min or 
            settings_dict['break_minutes'] != current_break_min):
            timer_engine.update_durations(settings_dict['work_minutes'], settings_dict['break_minutes'])
        
        # Audio Volume & Mute
        audio_manager.set_work_volume(settings_dict['work_volume'])
        audio_manager.set_break_volume(settings_dict['break_volume'])
        audio_manager.toggle_mute(settings_dict.get('is_muted', False))
        
        # Startup
        if settings_dict['run_at_startup'] != StartupManager.is_run_at_startup():
            StartupManager.set_run_at_startup(settings_dict['run_at_startup'])

    settings.settings_changed.connect(handle_settings_change)
    
    # Tray -> Settings / Exit
    def show_settings():
        settings.showNormal()
        settings.activateWindow()
        settings.raise_()
        
    tray_manager.show_settings_requested.connect(show_settings)
    tray_manager.quit_requested.connect(app.quit)
    
    # Tray -> Ghost Mode
    def handle_tray_ghost_toggle(enabled):
        widget.toggle_ghost_mode(enabled)
        tray_manager.update_ghost_state(enabled)
        
    tray_manager.toggle_ghost_requested.connect(handle_tray_ghost_toggle)

    # Tray -> Mute Toggle
    def handle_tray_mute_toggle(is_muted):
        # 1. Update Audio
        audio_manager.toggle_mute(is_muted)
        
        # 2. Persist
        # We need to update the settings file. We can fetch current from window + mute override
        # OR just load, update, save. Using SettingsWindow helper is risky if window is stale? 
        # Actually window is alive.
        current_s = settings.get_current_settings()
        current_s['is_muted'] = is_muted
        from utils.settings_manager import SettingsManager
        SettingsManager.save_settings(current_s)
        
    tray_manager.toggle_mute_requested.connect(handle_tray_mute_toggle)
    
    # Tray -> Work Log Toggle
    def handle_tray_work_log_toggle(enabled):
        # 1. Update Settings Persistence
        # Ensure SettingsWindow internal state is updated so get_current_settings() includes it
        settings.set_work_log_enabled(enabled)
        
        current_s = settings.get_current_settings()
        from utils.settings_manager import SettingsManager
        SettingsManager.save_settings(current_s)
        
        # 2. Update Tray State (optimization: tray likely triggered this, but good to be explicit)
        tray_manager.update_work_log_state(enabled)
        
    tray_manager.toggle_work_log_requested.connect(handle_tray_work_log_toggle)
    
    # Tray -> Review Logs
    def show_log_viewer():
        log_viewer.showNormal()
        log_viewer.activateWindow()
        log_viewer.raise_()
        
    tray_manager.review_logs_requested.connect(show_log_viewer)

    # Initialize
    # Sync visual defaults from Settings (which loaded from JSON)
    current_settings = settings.get_current_settings()
    # Note: 'is_muted' might be missing from get_current_settings() if we removed the UI element
    # So we'll fetch it from the raw loaded settings or re-read.
    # The settings window `current_settings` AT INIT TIME had it.
    initial_mute_state = settings.current_settings.get('is_muted', False)
    
    widget.current_bg_opacity = current_settings['bg_opacity']
    widget.current_text_opacity = current_settings['text_opacity']
    widget.current_text_size = current_settings['text_size']
    
    # Determine initial color based on state (likely 'work' on startup)
    # We can rely on settings defaults or logic.
    widget.current_text_color = current_settings['work_color']
    
    # Start Timer
    # Ensure UI matches init state (Work)
    widget.update_style(
        text_color=widget.current_text_color, 
        bg_opacity=widget.current_bg_opacity,
        text_opacity=widget.current_text_opacity,
        text_size=current_settings['text_size']
    )
    
    # Apply Initial Orange Settings
    widget.set_timer_style(current_settings.get('timer_style', 'orange'))
    widget.set_orange_opacity(current_settings.get('orange_opacity', 1.0))
    # Ensure initial mode is set (TimerEngine starts at Work)
    widget.set_mode("work") 
    timer_engine.start()
    
    # Apply initial Audio volumes
    audio_manager.set_work_volume(current_settings['work_volume'])
    audio_manager.set_break_volume(current_settings['break_volume'])
    audio_manager.toggle_mute(initial_mute_state)
    tray_manager.update_mute_state(initial_mute_state)
    

    
    # Initial Work Log State
    initial_work_log_state = current_settings.get('work_log_enabled', False)
    tray_manager.update_work_log_state(initial_work_log_state)
    
    # Initial Sync (Settings -> Widget)
    # Ensure startup registry matches our default (True) if not already set
    current_settings = settings.get_current_settings()
    if current_settings['run_at_startup'] and not StartupManager.is_run_at_startup():
        StartupManager.set_run_at_startup(True)

    widget.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
