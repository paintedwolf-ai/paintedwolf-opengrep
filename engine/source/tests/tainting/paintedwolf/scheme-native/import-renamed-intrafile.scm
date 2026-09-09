(use-modules ((web request) #:select ((request-uri . uri)) #:prefix http:))
(define (handler request)
  ;; ruleid: flow
  (sink (http:uri request)))
