(let [options {:root (source) ":root" "safe"}]
  (sink (get options ":root"))
  ;; ruleid: flow
  (sink (get options :root))
  ;; ruleid: flow
  (sink (:root options)))
(let [options {":root" (source) :root "safe"}]
  (sink (get options :root))
  (sink (:root options))
  ;; ruleid: flow
  (sink (get options ":root")))
(let [{root :root} {":root" (source) :root "safe"}]
  (sink root))
(let [{root ":root"} {:root (source) ":root" "safe"}]
  (sink root))
(let [{root :root} {:root (source) ":root" "safe"}]
  ;; ruleid: flow
  (sink root))
(let [{root ":root"} {":root" (source) :root "safe"}]
  ;; ruleid: flow
  (sink root))
(let [options {:root (source) ":root" "safe"} key :root]
  ;; ruleid: flow
  (sink (get options key)))
(let [options {":root" (source) :root "safe"} key :root]
  (sink (get options key)))
