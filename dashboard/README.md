# `clood-dashboard` — the client application for CloodCBR

This project demonstrates the use of AngularJS for CBR applications. The application interacts with the serverless functions of Clood through RESTful APIs.


## Getting Started

### Install Dependencies

* We get the tools the app depends on and the AngularJS code via `npm`, the [Node package manager][npm].

`npm` is preconfigured to automatically copy the downloaded AngularJS files to `app/lib` so you can simply do:

```
npm install
```

Behind the scenes this will also call `npm run copy-libs`, which copies the AngularJS files and other front end dependencies. After that, you should find out that you have two new directories in your project.

* `node_modules` - contains the npm packages for the tools we need
* `app/lib` - contains the AngularJS framework files and other front end dependencies

*Note copying the AngularJS files from `node_modules` to `app/lib` makes it easier to serve the files by a web server.*

### Run the Application

In the `app` directory, rename `env.sample.js` to `env.js` and edit file to specify the root URL for the serverless functions (i.e. set `base_api_url` value without a trailing slash).

We have preconfigured the project with a simple development web server. The simplest way to start this server is:

```
npm start
```

Now browse to the app at [`localhost:8000`][local-app-url].


## Directory Layout

```
app/                  --> all of the source files for the application
  app.css               --> default stylesheet
  core/                 --> all app specific modules
    version/              --> version related components
      version.js                 --> version module declaration and basic "version" value service
      version_test.js            --> "version" value service tests
      version-directive.js       --> custom directive that returns the current app version
      version-directive_test.js  --> version directive tests
      interpolate-filter.js      --> custom interpolation filter
      interpolate-filter_test.js --> interpolate filter tests
  cbr/                 --> the cbr view template and logic
    cbr.html            --> the partial template for cbr views
    views/              --> the partial template for phases of the cbr cycle
    cbr.js              --> the controller logic
    cbr.spec.js         --> tests of the cbr controller
  config/              --> the cbr config view template and logic
    config.html         --> the partial template for config views
    views/              --> the partial template cbr configuration pages
    config.js           --> the config controller logic
    config.spec.js      --> tests of the config controller
  projects/            --> the projects view template and logic
    projects.html       --> the partial template for cbr projects views
    projects.js         --> the projects controller logic
    projects.spec.js    --> tests of the projects controller
  app.js               --> main application module
  index.html            --> app layout file (the main html template file of the app)
e2e-tests/            --> end-to-end tests
  protractor-conf.js    --> Protractor config file
  scenarios.js          --> end-to-end scenarios to be run by Protractor
karma.conf.js         --> config file for running unit tests with Karma
package.json          --> Node.js specific metadata, including development tools dependencies
package-lock.json     --> Npm specific metadata, including versions of installed development tools dependencies
```


## Testing

There are two kinds of tests in the `clood-dashboard` application: Unit tests and end-to-end tests.

### Running Unit Tests

Tests are written in [Jasmine][jasmine], which we run with the [Karma][karma] test runner. We provide a Karma configuration file to run them.

* The configuration is found at `karma.conf.js`.
* The unit tests are found next to the code they are testing and have a `.spec.js` suffix (e.g. `cbr.spec.js`).

The easiest way to run the unit tests is to use the supplied npm script:

```
npm test
```

This script will start the Karma test runner to execute the unit tests. Moreover, Karma will start watching the source and test files for changes and then re-run the tests whenever any of them changes. This is the recommended strategy; if your unit tests are being run every time you save a file then you receive instant feedback on any changes that break the expected code functionality.

You can also ask Karma to do a single run of the tests and then exit. This is useful if you want to check that a particular version of the code is operating as expected. The project contains a predefined script to do this:

```
npm run test-single-run
```


<a name="e2e-testing"></a>
### Running End-to-End Tests

The `clood-dashboard` app comes with end-to-end tests, again written in [Jasmine][jasmine]. These tests are run with the [Protractor][protractor] End-to-End test runner. It uses native events and has special features for AngularJS applications.

* The configuration is found at `e2e-tests/protractor-conf.js`.
* The end-to-end tests are found in `e2e-tests/scenarios.js`.

Protractor simulates interaction with our web app and verifies that the application responds correctly. Therefore, our web server needs to be serving up the application, so that Protractor can interact with it.

**Before starting Protractor, open a separate terminal window and run:**

```
npm start
```

In addition, since Protractor is built upon WebDriver, we need to ensure that it is installed and up-to-date. The `clood-dashboard` project is configured to do this automatically before running the end-to-end tests, so you don't need to worry about it. If you want to manually update the WebDriver, you can run:

```
npm run update-webdriver
```

Once you have ensured that the development web server hosting our application is up and running, you can run the end-to-end tests using the supplied npm script:

```
npm run protractor
```

This script will execute the end-to-end tests against the application being hosted on the development server.

**Note:**
Under the hood, Protractor uses the [Selenium Standalone Server][selenium], which in turn requires the [Java Development Kit (JDK)][jdk] to be installed on your local machine. Check this by running `java -version` from the command line.

If JDK is not already installed, you can download it [here][jdk-download].



## Serving the Application Files

While AngularJS is client-side-only technology and it is possible to create AngularJS web apps that do not require a backend server at all, we  recommend serving the project files using a local web server during development to avoid issues with security restrictions (sandbox) in browsers. The sandbox implementation varies between browsers, but quite often prevents things like cookies, XHR, etc to function properly when an HTML page is opened via the `file://` scheme instead of `http://`.

### Running the App during Development

The `clood-dashboard` project comes preconfigured with a local development web server. It is a Node.js tool called [http-server][http-server]. You can start this web server with `npm start`, but you may choose to install the tool globally:

```
sudo npm install -g http-server
```

Then you can start your own development web server to serve static files from any folder by running:

```
http-server -a localhost -p 8000
```

Alternatively, you can choose to configure your own web server, such as Apache or Nginx. Just configure your server to serve the files under the `app/` directory.

### Running the App in Production

This really depends on how complex your app is and the overall infrastructure of your system, but the general rule is that all you need in production are the files under the `app/` directory.
Everything else should be omitted.

AngularJS apps are really just a bunch of static HTML, CSS and JavaScript files that need to be hosted somewhere they can be accessed by browsers.

If your AngularJS app is talking to the backend server via XHR or other means, you need to figure out what is the best way to host the static files to comply with the same origin policy if applicable. Usually this is done by hosting the files by the backend server or through reverse-proxying the backend server(s) and web server(s).


## Continuous Integration

### Travis CI

[Travis CI][travis] is a continuous integration service, which can monitor GitHub for new commits to your repository and execute scripts such as building the app or running tests. The `clood-dashboard` project contains a Travis configuration file, `.travis.yml`, which will cause Travis to run your tests when you push to GitHub.

You will need to enable the integration between Travis and GitHub. See the
[Travis website][travis-docs] for instructions on how to do this.



[angularjs]: https://angularjs.org/
[git]: https://git-scm.com/
[http-server]: https://github.com/indexzero/http-server
[jasmine]: https://jasmine.github.io/
[jdk]: https://wikipedia.org/wiki/Java_Development_Kit
[jdk-download]: http://www.oracle.com/technetwork/java/javase/downloads
[karma]: https://karma-runner.github.io/
[local-app-url]: http://localhost:8000
[node]: https://nodejs.org/
[npm]: https://www.npmjs.org/
[protractor]: http://www.protractortest.org/
[selenium]: http://docs.seleniumhq.org/
[travis]: https://travis-ci.org/
[travis-docs]: https://docs.travis-ci.com/user/getting-started
