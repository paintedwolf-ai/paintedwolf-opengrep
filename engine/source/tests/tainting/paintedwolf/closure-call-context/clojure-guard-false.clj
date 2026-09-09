(defn handler [value]
;; ok: closure-context
 (let [helper (fn [enabled] (if enabled value "safe"))] (sink (helper false))))
(register handler)
