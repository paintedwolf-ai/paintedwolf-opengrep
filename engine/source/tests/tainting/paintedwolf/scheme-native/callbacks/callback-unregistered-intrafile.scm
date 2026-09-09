(use-modules ((web server) #:select (run-server)))
(define (handler request body) (sink body))
