(use-modules ((web request) #:select (request-uri)) (example request))
(define (handler request) (sink (request-uri request)))
