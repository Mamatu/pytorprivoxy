import main
import time

def test_interrupt_initialization():
    start_time = time.time()
    import logging
    log = logging.getLogger("pytorprivoxy")
    stop_control = main.start_main_async(log_level = "INFO", start = (9000, 9001, 9002), stdout = True)
    time.sleep(15)
    main.stop_all()
    stop_control.stop()
    end_time = time.time()
    assert (end_time - start_time) <= 17

def test_interrupt_initialization():
    start_time = time.time()
    import logging
    log = logging.getLogger("pytorprivoxy")
    stop_control = main.start_main_async(log_level = "INFO", start = (9000, 9001, 9002), server = 9003, stdout = True)
    
    main.stop_all()
    end_time = time.time()
    assert (end_time - start_time) <= 100
