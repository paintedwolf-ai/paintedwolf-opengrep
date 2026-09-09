;; ruleid: async
(register handler {:port 8080 :async? true})
;; ruleid: sync
(register handler {:port 8080})
(register handler {:async? false})
(register handler options)
;; ruleid: async
(let [options {:async? true}] (register handler options))
;; ruleid: sync
(let [options {:port 8080}] (register handler options))

(let [options {:async? false}] (register handler options))
(let [options {:async? true} options {:async? false}] (register handler options))
(let [options {:async? true}]
  (let [options {:async? false}] (register handler options))
  ;; ruleid: async
  (register handler options))
(let [options {:async? true} copy options]
  ;; ruleid: async
  (register handler copy))
(let [options {:async? (runtime-mode)}] (register handler options))
(let [options {:nested {:async? true}}]
  ;; ruleid: sync
  (register handler options))
