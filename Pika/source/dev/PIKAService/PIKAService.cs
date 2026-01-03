namespace PIKAservice
{
    public class PIKAFuntion
    {
        private readonly ILogger _logger;

        public PIKAFuntion(ILoggerFactory loggerFactory)
        {
            _logger = loggerFactory.CreateLogger<PIKAFuntion>();
        }

        [Function("PIKAFuntion")]
        public HttpResponseData Run([HttpTrigger(AuthorizationLevel.Anonymous, "get", "post")] HttpRequestData req)
        {
            _logger.LogInformation("PIKAFuntion processed a request.");

            var response = req.CreateResponse(System.Net.HttpStatusCode.OK);
            response.Headers.Add("Content-Type", "text/plain; charset=utf-8");
            response.WriteString("Welcome to PIKAservice Azure Function!");

            return response;
        }
    }
}