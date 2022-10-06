def projectIndexError():
  body = {}
  body['error'] = "ResourceNotFound"
  body['message'] = "Could not find a project_db index"
  body['detail'] = "Create a new project to generate the projects index"

  return body

def projectGetError():
  body = {}
  body['error'] = "ProjectNotFound"
  body['message'] = "Could not find the specified project"
  body['detail'] = "Please check that the project ID is correct"

  return body

def projectNameError():
  body = {}
  body['error'] = "ProjectNameError"
  body['message'] = "A new project has to specify a name"
  body['detail'] = "Please specify a name attribute when creating a new project"

  return body

def projectDuplicateError():
  body = {}
  body['error'] = "ProjectDuplicateError"
  body['message'] = "Casebase already exists"
  body['detail'] = "Choose a different name for the casebase"

  return body

def projectCreateError():
  body = {}
  body['error'] = "ProjectCreateError"
  body['message'] = "Failed to create new project"
  body['detail'] = "Contact system administrator for additional information."

  return body

def projectUpdateError():
  body = {}
  body['error'] = "ProjectUpdateError"
  body['message'] = "Failed to update project"
  body['detail'] = "Contact system administrator for additional information."

  return body

def projectDeleteError():
  body = {}
  body['error'] = "ProjectDeleteError"
  body['message'] = "Failed to delete project"
  body['detail'] = "Contact system administrator for additional information."

  return body