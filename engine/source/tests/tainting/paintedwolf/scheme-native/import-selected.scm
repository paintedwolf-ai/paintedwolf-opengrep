(use-modules ((web request) #:select (request-uri)))
(define (handler request)
  ;; ruleid: flow
  (sink (request-uri request)))
