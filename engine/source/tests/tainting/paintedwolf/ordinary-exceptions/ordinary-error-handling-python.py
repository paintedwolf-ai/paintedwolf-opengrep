def report_error():
    try:
        external(source())
    except Exception as error:
        if error.args:
            logger.error(error.args[0])
        report(error, error.__cause__)
        raise

try:
    report_error()
except Exception as error:
    logger.error(error)
