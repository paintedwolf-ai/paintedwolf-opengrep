(use-modules ((web request) #:select (request-uri)))
(define (handler request request-uri) (sink (request-uri request)))
