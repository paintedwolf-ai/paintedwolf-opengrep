(ns app)
(defn flow [unknown]
  (sink (or 0 (source)))
  (or 0 (sink (source)))
  ;; ruleid: flow
  (sink (and 0 (source)))
  ;; ruleid: flow
  (and 0 (sink (source)))
  (let [value 0]
    ;; ruleid: flow
    (if value (sink (source)) "fixed")
    (if value "fixed" (sink (source))))
  (sink (or 0.0 (source)))
  (or 0.0 (sink (source)))
  ;; ruleid: flow
  (sink (and 0.0 (source)))
  ;; ruleid: flow
  (and 0.0 (sink (source)))
  (let [value 0.0]
    ;; ruleid: flow
    (if value (sink (source)) "fixed")
    (if value "fixed" (sink (source))))
  (sink (or "" (source)))
  (or "" (sink (source)))
  ;; ruleid: flow
  (sink (and "" (source)))
  ;; ruleid: flow
  (and "" (sink (source)))
  (let [value ""]
    ;; ruleid: flow
    (if value (sink (source)) "fixed")
    (if value "fixed" (sink (source))))
  (sink (or "0" (source)))
  (or "0" (sink (source)))
  ;; ruleid: flow
  (sink (and "0" (source)))
  ;; ruleid: flow
  (and "0" (sink (source)))
  (let [value "0"]
    ;; ruleid: flow
    (if value (sink (source)) "fixed")
    (if value "fixed" (sink (source))))
  (sink (or :safe (source)))
  (or :safe (sink (source)))
  ;; ruleid: flow
  (sink (and :safe (source)))
  ;; ruleid: flow
  (and :safe (sink (source)))
  (let [value :safe]
    ;; ruleid: flow
    (if value (sink (source)) "fixed")
    (if value "fixed" (sink (source))))
  (sink (or [] (source)))
  (or [] (sink (source)))
  ;; ruleid: flow
  (sink (and [] (source)))
  ;; ruleid: flow
  (and [] (sink (source)))
  (let [value []]
    ;; ruleid: flow
    (if value (sink (source)) "fixed")
    (if value "fixed" (sink (source))))
  (sink (or {} (source)))
  (or {} (sink (source)))
  ;; ruleid: flow
  (sink (and {} (source)))
  ;; ruleid: flow
  (and {} (sink (source)))
  (let [value {}]
    ;; ruleid: flow
    (if value (sink (source)) "fixed")
    (if value "fixed" (sink (source))))
  (sink (or #{} (source)))
  (or #{} (sink (source)))
  ;; ruleid: flow
  (sink (and #{} (source)))
  ;; ruleid: flow
  (and #{} (sink (source)))
  (let [value #{}]
    ;; ruleid: flow
    (if value (sink (source)) "fixed")
    (if value "fixed" (sink (source))))
  ;; ruleid: flow
  (sink (or false (source)))
  ;; ruleid: flow
  (or false (sink (source)))
  (sink (and false (source)))
  (and false (sink (source)))
  (let [value false]
    (if value (sink (source)) "fixed")
    ;; ruleid: flow
    (if value "fixed" (sink (source))))
  ;; ruleid: flow
  (sink (or nil (source)))
  ;; ruleid: flow
  (or nil (sink (source)))
  (sink (and nil (source)))
  (and nil (sink (source)))
  (let [value nil]
    (if value (sink (source)) "fixed")
    ;; ruleid: flow
    (if value "fixed" (sink (source))))
  (sink (or true (source)))
  (or true (sink (source)))
  ;; ruleid: flow
  (sink (and true (source)))
  ;; ruleid: flow
  (and true (sink (source)))
  (let [value true]
    ;; ruleid: flow
    (if value (sink (source)) "fixed")
    (if value "fixed" (sink (source))))
  ;; ruleid: flow
  (sink (or unknown (source)))
  ;; ruleid: flow
  (sink (and unknown (source)))
)
