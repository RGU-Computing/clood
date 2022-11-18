def projectIndexException():
  body = {}
  body['type'] = "ProjectDBNotFound"
  body['message'] = "Could not find a project_db index"
  body['detail'] = "Create a new project to generate the projects index"

  return body

def projectGetException():
  body = {}
  body['type'] = "ProjectNotFound"
  body['message'] = "Could not find the specified project"
  body['detail'] = "Please check that the project ID is correct"

  return body

def projectNameException():
  body = {}
  body['type'] = "ProjectNameException"
  body['message'] = "A new project has to specify a name"
  body['detail'] = "Please specify a name attribute when creating a new project"

  return body

def projectDuplicateException():
  body = {}
  body['type'] = "ProjectDuplicateException"
  body['message'] = "Casebase already exists"
  body['detail'] = "Choose a different name for the casebase"

  return body

def projectCreateException():
  body = {}
  body['type'] = "ProjectCreateException"
  body['message'] = "Failed to create new project"
  body['detail'] = "Contact system administrator for additional information."

  return body

def projectUpdateException():
  body = {}
  body['type'] = "ProjectUpdateException"
  body['message'] = "Failed to update project"
  body['detail'] = "Contact system administrator for additional information"

  return body

def projectDeleteException():
  body = {}
  body['type'] = "ProjectDeleteException"
  body['message'] = "Failed to delete project"
  body['detail'] = "Contact system administrator for additional information"

  return body

def casebaseGetException():
  body = {}
  body['type'] = "CasebaseNotFound"
  body['message'] = "Could not find a casebase attached to the project"
  body['detail'] = "Make sure you have added data to the project"

  return body

def caseDeleteException():
  body = {}
  body['type'] = "CaseebaseDeleteException"
  body['message'] = "Could not delete the casebase for the specified project"
  body['detail'] = "Check to see that the project id is correct"

  return body

def caseGetException():
  body = {}
  body['type'] = "CaseNotFoundException"
  body['message'] = "Could not find the specified case"
  body['detail'] = "Make sure that the case id is correct"

  return body

def caseUpdateException():
  body = {}
  body['type'] = "CaseUpdateException"
  body['message'] = "Could not update the specified case"
  body['detail'] = "Contact system administrator for additional information"

  return body

def caseDeleteException():
  body = {}
  body['type'] = "CaseDeleteException"
  body['message'] = "Could not delete the specified case"
  body['detail'] = "Contact system administrator for additional information"

  return body

def caseDuplicateException():
  body = {}
  body['type'] = "CaseDuplicateException"
  body['message'] = "The case already exists in the casebase"
  body['detail'] = "Enable duplicate cases within the project if you wish to store identical cases"

  return body

def authException():
  body = {}
  body['type'] = "AuthException"
  body['message'] = "Could not authenticate user"
  body['detail'] = "Check that the user credentials are correct"

  return body

def tokenIndexException():
  body = {}
  body['type'] = "TokenDBNotFound"
  body['message'] = "Could not find a token_db index"
  body['detail'] = "Contact system administrator for additional information"

  return body

def tokenNameException():
  body = {}
  body['type'] = "TokenNameException"
  body['message'] = "A new token has to specify a name"
  body['detail'] = "Please specify a name attribute when creating a new token"

  return body

def tokenCreateException():
  body = {}
  body['type'] = "TokenCreateException"
  body['message'] = "Failed to create new token"
  body['detail'] = "Contact system administrator for additional information"

  return body

def tokenDeleteException():
  body = {}
  body['type'] = "TokenDeleteException"
  body['message'] = "Failed to delete token"
  body['detail'] = "Contact system administrator for additional information"

  return body