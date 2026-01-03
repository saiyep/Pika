using System;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Extensions.Logging;

namespace PIKAService
{
    public class PIKAFunction
    {
        private readonly ILogger _logger;

        public PIKAFunction(ILoggerFactory loggerFactory)
        {
            _logger = loggerFactory.CreateLogger<PIKAFunction>();
        }

        [Function("PIKAFunction")]
        public HttpResponseData Run([HttpTrigger(AuthorizationLevel.Anonymous, "get", "post")] HttpRequestData req)
        {
            _logger.LogInformation("PIKAFunction processed a request.");

            var response = req.CreateResponse(System.Net.HttpStatusCode.OK);
            response.Headers.Add("Content-Type", "text/plain; charset=utf-8");
            response.WriteString("Welcome to PIKAService Azure Function!");

            return response;
        }
    }
}