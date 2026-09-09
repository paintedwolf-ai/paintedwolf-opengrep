# ruleid: flow
Use-Model (New-Model)
$model = New-Model
# ruleid: flow
Use-Model $model
# ruleid: flow
New-Model | Use-Model
# ruleid: flow
Use-Model -Value (New-Model)
# ok: flow
Use-Model 'safe'
# ok: flow
Use-Model (Other-Factory)
# ok: flow
Use-Model ((New-Model), 'safe')
# ok: flow
Use-Model (Convert-Model (New-Model))
