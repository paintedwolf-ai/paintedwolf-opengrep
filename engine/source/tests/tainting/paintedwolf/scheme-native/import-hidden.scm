(use-modules ((web request) #:hide (request-uri)))
(define (handler request) (sink (request-uri request)))
