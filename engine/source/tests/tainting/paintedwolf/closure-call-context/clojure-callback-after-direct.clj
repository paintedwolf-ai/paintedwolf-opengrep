(defn handler [value]
;; ruleid: closure-context
 (let [helper (fn [enabled] (if enabled (sink value) "safe"))] (helper false) (register helper)))
(register handler)
