using System.Net;
using System.Net.Http;

namespace Timesheet.Admin.Services;

/// <summary>
/// Adds the X-CSRF-Token header to state-changing requests. The token is the value of
/// the readable ts_csrf cookie the API sets at login (the session cookie itself is
/// HttpOnly and only handled by the cookie container).
/// </summary>
public sealed class CsrfHandler(CookieContainer cookies, Uri baseUri) : DelegatingHandler
{
    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        if (request.Method != HttpMethod.Get
            && request.Method != HttpMethod.Head
            && request.Method != HttpMethod.Options)
        {
            var token = cookies.GetCookies(baseUri)["ts_csrf"]?.Value;
            if (!string.IsNullOrEmpty(token))
            {
                request.Headers.Remove("X-CSRF-Token");
                request.Headers.Add("X-CSRF-Token", token);
            }
        }

        return base.SendAsync(request, cancellationToken);
    }
}
