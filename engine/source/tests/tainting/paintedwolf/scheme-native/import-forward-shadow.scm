(use-modules ((web request) #:select (request-uri)))
(define (handler request) (sink (request-uri request)))
(define (request-uri request) "fixed")
