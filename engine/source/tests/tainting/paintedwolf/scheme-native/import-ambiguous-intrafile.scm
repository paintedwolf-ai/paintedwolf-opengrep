(use-modules (web request) (example request))
(define (handler request) (sink (request-uri request)))
